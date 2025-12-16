import os
import subprocess
import time
from contextlib import contextmanager

class VaultEngine:
    """
    Verantwoordelijk voor alle systeem-operaties:
    Grootte berekenen, DMG aanmaken, Mounten, Kopiëren, Encrypten.
    Weet NIETS van de GUI.
    """
    
    def calculate_size_mb(self, source_path):
        """Berekent grootte + 10% buffer + 50MB overhead"""
        total_size = 0
        for dirpath, _, filenames in os.walk(source_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        
        size_mb = int(total_size / (1024 * 1024))
        return int(size_mb * 1.1) + 50

    def cleanup(self, path):
        """Veilige verwijdering van bestand"""
        if os.path.exists(path):
            os.remove(path)

    @contextmanager
    def mount_context(self, dmg_path, mount_point):
        """
        Dit is de Context Manager.
        Het garandeert dat 'hdiutil detach' ALTIJD wordt aangeroepen,
        zelfs als de code in het 'with' blok crasht.
        """
        # 1. Setup (Mounten)
        # Zorg eerst dat mountpunt vrij is
        subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], capture_output=True)
        
        cmd = ['hdiutil', 'attach', dmg_path, '-mountpoint', mount_point, '-quiet', '-noverify']
        subprocess.run(cmd, check=True, capture_output=True)
        
        try:
            yield  # Hier draait de code binnen het 'with' blok
        finally:
            # 2. Teardown (Altijd Detachen)
            # We proberen het een paar keer voor het geval de disk 'busy' is
            for _ in range(3):
                res = subprocess.run(['hdiutil', 'detach', mount_point, '-quiet', '-force'], capture_output=True)
                if res.returncode == 0:
                    break
                time.sleep(1)

    def create_vault(self, source, dest_folder, name, password, progress_callback=None):
        """
        De hoofdfunctie die alles aanstuurt.
        progress_callback: een functie om status-updates naar de GUI te sturen.
        """
        def log(msg):
            if progress_callback: progress_callback(msg)

        dmg_final = os.path.join(dest_folder, f"{name}.dmg")
        dmg_temp = os.path.join(dest_folder, f"temp_{name}.dmg")
        vol_name = "BeveiligdVolume"
        mount_point = f"/Volumes/{vol_name}"

        # 0. Schoonmaak vooraf
        self.cleanup(dmg_temp)

        try:
            # 1. Grootte
            log("📏 Stap 1: Grootte berekenen...")
            size_mb = self.calculate_size_mb(source)
            size_arg = f"{size_mb}m"
            log(f"   -> Geschatte grootte: {size_arg}")

            # 2. Tijdelijke DMG
            log("🔨 Stap 2: Tijdelijke werkschijf maken...")
            subprocess.run([
                'hdiutil', 'create', '-size', size_arg, '-fs', 'HFS+J', 
                '-volname', vol_name, '-type', 'UDIF', '-o', dmg_temp
            ], check=True, capture_output=True)

            # 3. Mounten & Kopiëren (Binnen de veilige Context Manager)
            log("🔌 Stap 3: Koppelen en kopiëren...")
            
            with self.mount_context(dmg_temp, mount_point):
                # We zitten nu in de veilige zone. Als rsync faalt, wordt er toch gedetached.
                log("📂 Bezig met kopiëren (rsync)...")
                res = subprocess.run(['rsync', '-av', f'{source}/', mount_point], capture_output=True, text=True)
                if res.returncode != 0:
                    raise Exception(f"Rsync fout: {res.stderr}")
            
            log("✅ Kopiëren voltooid en schijf ontkoppeld.")

            # 4. Converteren & Encrypten
            log("🔒 Stap 4: Versleutelen...")
            if os.path.exists(dmg_final):
                os.remove(dmg_final) # Overschrijf oude versie indien nodig

            cmd_convert = [
                'hdiutil', 'convert', dmg_temp, '-format', 'UDZO', 
                '-o', dmg_final, '-encryption', 'AES-256', '-stdinpass'
            ]
            
            process = subprocess.Popen(
                cmd_convert, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, text=True
            )
            # Veilig wachtwoord sturen (zonder \n)
            stdout, stderr = process.communicate(input=password)

            if process.returncode != 0:
                raise Exception(f"Encryptie fout: {stderr}")

            self.cleanup(dmg_temp)
            log(f"🎉 Succes! Kluis staat in: {dmg_final}")
            return True, dmg_final

        except Exception as e:
            self.cleanup(dmg_temp)
            log(f"❌ Fout opgetreden: {str(e)}")
            return False, str(e)