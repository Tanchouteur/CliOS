import os

def ui_loop(runtime, stop_event):
    """Interface de débogage en ligne de commande (CLI)."""
    while not stop_event.is_set():
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\033[H\033[2J", end="")
        print("=" * 45)
        print("   CONSOLE DE DEBUG TELEMETRIQUE (CLIOS)")
        print("=" * 45)

        snapshot = runtime.snapshot()
        populated_domains = {name: values for name, values in snapshot.domains.items() if values}

        if not populated_domains:
            print("\nEn attente du flux de donnees...")
        else:
            for domain, values in populated_domains.items():
                print(f"\n[{domain}]")
                for key in sorted(values):
                    val = values[key]
                    if isinstance(val, bool):
                        val = "\033[92mON\033[0m" if val else "\033[91mOFF\033[0m"
                    elif isinstance(val, float):
                        val = f"{val:.3f}"
                    print(f" {key:<25} : {val}")

        print("\n[Ctrl+C pour interrompre le processus]")
        stop_event.wait(0.1)
