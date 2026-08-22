import QtQuick
import "../state" as S
import "../shared_pages/components" as C

Item {
    id: root
    objectName: "appShell"
    property string route: "home"
    property var history: ["home"]
    property string pendingCommand: ""
    property bool recoveryOpened: false

    readonly property var routes: ["home", "menu", "appearance", "vehicle", "services", "system", "diagnostic", "developer"]
    readonly property var confirmations: ({
        reset_a: ["Remettre Trip A à zéro ?", "La distance Trip A sera effacée.", "REMETTRE À ZÉRO", true],
        reset_b: ["Remettre Trip B à zéro ?", "La distance et la moyenne Trip B seront effacées.", "REMETTRE À ZÉRO", true],
        reset_maintenance: ["Confirmer la révision ?", "Le compteur d’entretien repartira sur un intervalle complet.", "CONFIRMER", false],
        end_trip: ["Terminer le trajet ?", "Les statistiques seront enregistrées avant la clôture.", "TERMINER", true],
        quit: ["Quitter CliOS ?", "Les écritures et services seront arrêtés proprement.", "QUITTER", true],
        restart: ["Redémarrer CliOS ?", "Le cockpit et les services seront relancés.", "REDÉMARRER", true],
        reboot: ["Redémarrer le système ?", "Le Raspberry Pi sera redémarré proprement.", "REDÉMARRER", true],
        shutdown: ["Éteindre le système ?", "Le Raspberry Pi sera arrêté proprement.", "ÉTEINDRE", true],
        maintenance: ["Ouvrir la maintenance ?", "Les commandes système avancées vont être affichées.", "OUVRIR", false],
        toggle_overlayfs: ["Basculer OverlayFS ?", "La protection de la carte SD sera modifiée et un redémarrage sera requis.", "BASCULER", true]
    })

    function openRoute(nextRoute) {
        if (routes.indexOf(nextRoute) < 0) nextRoute = "menu"
        if (nextRoute === route) return
        route = nextRoute
        history.push(nextRoute)
    }

    function back() {
        if (route === "menu") {
            route = "home"
            history = ["home"]
        } else if (route !== "home") {
            route = "menu"
            history = ["home", "menu"]
        }
    }

    function requestCommand(command) {
        if (command === "resume_trip" || command === "pause_trip" || command.indexOf("set_") === 0) {
            bridge.executeUiCommand(command, S.UiState.speed)
            return
        }
        const data = confirmations[command]
        if (!data) {
            bridge.executeUiCommand(command, S.UiState.speed)
            return
        }
        pendingCommand = command
        confirm.title = data[0]
        confirm.message = data[1]
        confirm.acceptText = data[2]
        confirm.dangerous = data[3]
        confirm.visible = true
    }

    DashboardHost {
        anchors.fill: parent
        visible: root.route === "home"
        onSettingsRequested: route => root.openRoute(route)
        onCommandRequested: command => root.requestCommand(command)
    }

    SettingsShell {
        anchors.fill: parent
        visible: root.route !== "home"
        route: root.route
        onBackRequested: root.back()
        onCommandRequested: command => root.requestCommand(command)
        onNavigateRequested: route => root.openRoute(route)
    }

    MaintenanceOverlay {
        id: maintenanceOverlay; z: 9200
        onCommandRequested: command => root.requestCommand(command)
    }
    Connections {
        target: bridge
        ignoreUnknownSignals: true
        function onOpenMaintenanceRequested() { maintenanceOverlay.open() }
    }

    C.ConfirmDialog {
        id: confirm
        z: 9300
        onRejected: { visible = false; root.pendingCommand = "" }
        onAccepted: {
            visible = false
            const command = root.pendingCommand
            root.pendingCommand = ""
            if (command === "maintenance") maintenanceOverlay.open()
            else bridge.executeUiCommand(command, S.UiState.speed)
        }
    }

    NotificationCenter { z: 9400 }

    Timer {
        interval: 500; running: !root.recoveryOpened; repeat: true
        onTriggered: {
            if (S.UiState.recoveryMode) {
                root.recoveryOpened = true
                root.openRoute("vehicle")
            }
        }
    }
}
