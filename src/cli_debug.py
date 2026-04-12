import os

def ui_loop(api, stop_event):
    """Interface de débogage en ligne de commande (CLI)."""
    while not stop_event.is_set():
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\033[H\033[2J", end="")
        print("=" * 45)
        print("   CONSOLE DE DEBUG TELEMETRIQUE (CLIOS)")
        print("=" * 45)

        data_dict = api._data.copy()

        if not data_dict:
            print("\nEn attente du flux de donnees...")
        else:
            for key in sorted(data_dict.keys()):
                val = data_dict[key]
                if isinstance(val, bool):
                    status = "\033[92mON\033[0m" if val else "\033[91mOFF\033[0m"
                    print(f" {key:<25} : {status}")
                elif isinstance(val, float):
                    print(f" {key:<25} : {val:.3f}")
                else:
                    print(f" {key:<25} : {val}")

        print("\n[Ctrl+C pour interrompre le processus]")
        stop_event.wait(0.1)