import QtQuick
import "../state" as S
import "../style" as T
import "../shared_pages/components" as C

Item {
    id: root
    objectName: "appShell"
    property string route: "home"
    property string requestedRoute: "driving"
    property string pendingCommand: ""
    property string pendingProfile: ""
    property bool recoveryOpened: false
    property bool waitingForDashboard: false

    readonly property var confirmations: ({
        reset_a: ["Remettre Trip A à zéro ?", "La distance Trip A sera effacée.", "REMETTRE À ZÉRO", true],
        reset_b: ["Remettre Trip B à zéro ?", "La distance et la moyenne Trip B seront effacées.", "REMETTRE À ZÉRO", true],
        reset_maintenance: ["Confirmer la révision ?", "Le compteur d’entretien repartira sur un intervalle complet.", "CONFIRMER", false],
        end_trip: ["Terminer le trajet ?", "Les statistiques seront enregistrées avant la clôture.", "TERMINER", true],
        quit: ["Quitter CliOS ?", "Les écritures et services seront arrêtés proprement.", "QUITTER", true],
        restart: ["Relancer CliOS ?", "Le cockpit et les services seront relancés.", "RELANCER", true],
        reboot: ["Redémarrer le système ?", "Le Raspberry Pi sera redémarré proprement.", "REDÉMARRER", true],
        shutdown: ["Éteindre le système ?", "Le Raspberry Pi sera arrêté proprement.", "ÉTEINDRE", true],
        toggle_overlayfs: ["Modifier la protection SD ?", "La configuration OverlayFS changera et un redémarrage sera requis.", "MODIFIER", true],
        update_activate: ["Activer la mise à jour ?", "CliOS redémarrera pour charger la nouvelle version.", "ACTIVER", true],
        update_rollback: ["Revenir à la version précédente ?", "CliOS redémarrera après le retour arrière.", "RETOUR ARRIÈRE", true]
    })

    function canonicalRoute(nextRoute) {
        if (nextRoute === "menu") return "driving"
        if (nextRoute === "diagnostic") return "vehicle"
        if (nextRoute === "transmission" || nextRoute === "vehicle_maintenance") return "vehicle"
        if (nextRoute === "services" || nextRoute === "developer") return "advanced"
        if (nextRoute === "profiles" || nextRoute === "can" || nextRoute === "logs") return "advanced"
        if (nextRoute === "leds" || nextRoute === "styles" || nextRoute === "accent") return "appearance"
        if (["maintenance", "network", "updates", "storage", "power"].indexOf(nextRoute) >= 0) return "system"
        if (["driving", "appearance", "vehicle", "system", "advanced"].indexOf(nextRoute) >= 0) return nextRoute
        return "driving"
    }

    function openRoute(nextRoute) {
        if (nextRoute === "home") { route = "home"; return }
        requestedRoute = nextRoute
        route = canonicalRoute(nextRoute)
    }

    function requestCommand(command) {
        if (command.indexOf("activate_profile:") === 0) {
            pendingProfile = command.substring("activate_profile:".length)
            confirm.title = "Activer ce profil véhicule ?"
            confirm.message = "CliOS redémarrera automatiquement après l’activation du profil « " + pendingProfile + " »."
            confirm.acceptText = "ACTIVER ET RELANCER"
            confirm.dangerous = false
            confirm.visible = true
            return
        }
        if (command === "resume_trip" || command === "pause_trip" || command.indexOf("set_") === 0
                || command.indexOf("wifi_") === 0 || command === "diagnostic_scan") {
            bridge.executeUiCommand(command, S.UiState.speed)
            return
        }
        const data = confirmations[command]
        if (!data) { bridge.executeUiCommand(command, S.UiState.speed); return }
        pendingCommand = command
        confirm.title = data[0]; confirm.message = data[1]; confirm.acceptText = data[2]
        confirm.dangerous = data[3]; confirm.visible = true
    }

    function applyStyle(styleId) {
        if (styleId === T.StyleManager.styleId) return
        waitingForDashboard = true
        T.StyleManager.selectStyle(styleId)
    }

    DashboardHost {
        anchors.fill: parent
        visible: root.route === "home"
        onSettingsRequested: route => root.openRoute(route)
        onCommandRequested: command => root.requestCommand(command)
        onDashboardReady: if (root.waitingForDashboard) {
            root.waitingForDashboard = false
            root.route = "home"
        }
    }

    SettingsShell {
        anchors.fill: parent
        visible: root.route !== "home"
        route: root.route
        requestedRoute: root.requestedRoute
        onCockpitRequested: root.route = "home"
        onCommandRequested: command => root.requestCommand(command)
        onNavigateRequested: route => root.openRoute(route)
        onStyleRequested: styleId => root.applyStyle(styleId)
    }

    Connections {
        target: bridge; ignoreUnknownSignals: true
        function onOpenMaintenanceRequested() { root.openRoute("maintenance") }
    }

    C.ConfirmDialog {
        id: confirm
        objectName: "globalConfirmDialog"
        z: 9300
        onRejected: { visible = false; root.pendingCommand = ""; root.pendingProfile = "" }
        onAccepted: {
            visible = false
            if (root.pendingProfile) {
                const profile = root.pendingProfile
                root.pendingProfile = ""
                if (bridge.setActiveProfile(profile)) bridge.restartApplication()
                return
            }
            const command = root.pendingCommand
            root.pendingCommand = ""
            bridge.executeUiCommand(command, S.UiState.speed)
        }
    }

    C.TripRecoveryDialog {
        z: 9350
        available: S.UiState.tripResumeAvailable
        secondsRemaining: S.UiState.tripResumeSeconds
        tripSummary: S.UiState.resumableTrip
        onResumeRequested: bridge.executeUiCommand("resume_trip", S.UiState.speed)
        onNewTripRequested: bridge.executeUiCommand("new_trip", S.UiState.speed)
    }

    NotificationCenter { z: 9400 }
    Timer {
        interval: 500; running: !root.recoveryOpened; repeat: true
        onTriggered: if (S.UiState.recoveryMode) {
            root.recoveryOpened = true
            root.openRoute("advanced")
        }
    }
}
