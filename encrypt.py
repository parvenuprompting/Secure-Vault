import subprocess
import os
import time
import sys

def ruim_op(tijdelijk_pad_dmg, mount_punt):
    """Ruimt tijdelijke bestanden en gekoppelde volumes op."""
    # Probeer stil te ontkoppelen
    subprocess.run(['hdiutil', 'detach', mount_punt, '-quiet', '-force'], capture_output=True)
    
    if os.path.exists(tijdelijk_pad_dmg):
        try:
            os.remove(tijdelijk_pad_dmg)
        except OSError:
            pass

def beveilig_map_met_wachtwoord(bron_pad, doel_map, dmg_naam, volume_naam="Beveiligd Volume"):
    
    # 1. Paden instellen
    print(f"--- Start Beveiliging van Map: {bron_pad} ---")
    
    dmg_bestand = os.path.join(doel_map, f"{dmg_naam}.dmg")
    tijdelijk_pad_dmg = os.path.join(doel_map, f"tijdelijk_{dmg_naam}.dmg")
    mount_punt = f"/Volumes/{volume_naam}"
    
    # Even schoon schip maken voor de zekerheid
    ruim_op(tijdelijk_pad_dmg, mount_punt)

    if not os.path.isdir(bron_pad):
        print(f"Fout: Bronmap '{bron_pad}' niet gevonden.")
        return

    schatting_grootte = "1g"
    
    # ----------------------------------------------------------------------------------

    # 2. Creëer tijdelijke werkschijf (Stil)
    print(f"\nStap 1/4: Creëren van tijdelijke werkschijf...")
    try:
        subprocess.run([
            'hdiutil', 'create', '-size', schatting_grootte, 
            '-fs', 'HFS+J', '-volname', volume_naam, 
            '-type', 'UDIF', '-o', tijdelijk_pad_dmg
        ], capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Fout bij aanmaken: {e.stderr}")
        return
    
    # ----------------------------------------------------------------------------------

    # 3. Koppel werkschijf (Stil)
    print("\nStap 2/4: Koppelen van de werkschijf...")
    try:
        subprocess.run([
            'hdiutil', 'attach', tijdelijk_pad_dmg, 
            '-mountpoint', mount_punt, 
            '-quiet', '-noverify'
        ], check=True)
        time.sleep(2) 
    except subprocess.CalledProcessError:
        ruim_op(tijdelijk_pad_dmg, mount_punt)
        return

    # ----------------------------------------------------------------------------------

    # 4. Kopieer bestanden
    print(f"\nStap 3/4: Bestanden kopiëren...")
    try:
        subprocess.run(['rsync', '-av', f'{bron_pad}/', mount_punt], check=True)
    except subprocess.CalledProcessError:
        ruim_op(tijdelijk_pad_dmg, mount_punt)
        return

    # ----------------------------------------------------------------------------------

    # 5. Converteren en Versleutelen (MET OS.SYSTEM)
    print(f"\nStap 4/4: Versleutelen...")
    
    # Eerst ontkoppelen
    subprocess.run(['hdiutil', 'detach', mount_punt, '-quiet', '-force'], capture_output=True)
    
    print("\n⚠️  LET OP: Type nu zelf je wachtwoord in en druk op ENTER.")
    print("⚠️  Bevestig daarna nogmaals met ENTER.")
    print("---------------------------------------------------------------")
    
    # We bouwen het commando als een string
    # We gebruiken quotes '' om de paden voor het geval er spaties in staan
    commando = f"hdiutil convert '{tijdelijk_pad_dmg}' -format UDZO -o '{dmg_bestand}' -encryption AES-256"
    
    # os.system geeft de volledige controle aan de terminal, dit voorkomt de invoer-fout
    resultaat = os.system(commando)
    
    if resultaat == 0:
        os.remove(tijdelijk_pad_dmg)
        print(f"\n✅ **Succes!** De map is beveiligd opgeslagen.")
        print(f"Locatie: {dmg_bestand}")
    else:
        print("\n❌ Er ging iets mis bij het versleutelen (misschien typfout in wachtwoord?).")
        ruim_op(tijdelijk_pad_dmg, mount_punt)

if __name__ == '__main__':
    # Detecteer paden
    PROJECT_PAD_BASIS = os.path.join(os.path.expanduser('~'), "Desktop", "EncryptieTest")
    BRON_MAP = os.path.join(PROJECT_PAD_BASIS, "GeheimeData")  
    DOEL_MAP = PROJECT_PAD_BASIS           
    DMG_NAAM = "MijnGeheimeDocumenten"                
    
    # Maak testdata als het niet bestaat
    if not os.path.exists(BRON_MAP):
        os.makedirs(BRON_MAP, exist_ok=True)
        with open(os.path.join(BRON_MAP, "test.txt"), "w") as f:
            f.write("Dit is een geheim document.")
        
    beveilig_map_met_wachtwoord(BRON_MAP, DOEL_MAP, DMG_NAAM)