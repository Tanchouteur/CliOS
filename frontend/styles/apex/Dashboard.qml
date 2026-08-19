import QtQuick
import QtQuick.Layouts
import "../../style" as T
import "../../state" as S
import "components"
import "pages"

// ══════════════════════════════════════════════════════════════════════════════
//  APEX Dashboard — CliOS · 1920×720 · Tactile · Console centrale
//  Fond vivant + effets 3D + animations constantes
// ══════════════════════════════════════════════════════════════════════════════
Item {
    id: root
    width:  1920
    height: 720
    clip:   true

    objectName: "apexDashboardRoot"

    // ── État de navigation ────────────────────────────────────────────────────
    property string currentTab: "drive"

    // Actions confirmées
    property string pendingAction: ""
    property string pendingTitle:  ""
    property string pendingMsg:    ""
    property bool   pendingDanger: false

    function navigate(tab) {
        if (tab === currentTab) return
        currentTab = tab
        var src = {
            drive: Qt.resolvedUrl("pages/ApexDrivePage.qml"),
            perf:  Qt.resolvedUrl("pages/ApexPerfPage.qml"),
            menu:  Qt.resolvedUrl("pages/ApexMenuPage.qml")
        }
        if (src[tab]) pageLoader.source = src[tab]
    }

    function askConfirmation(action) {
        if (action === "resume_trip") { bridge.resumeTripSession(); return }

        var copy = {
            reset_a:            ["Remettre Trip A à zéro ?",       "La distance Trip A sera effacée.",                               "REMETTRE À ZÉRO",      true  ],
            reset_b:            ["Remettre Trip B à zéro ?",       "Distance et consommation Trip B seront effacées.",               "REMETTRE À ZÉRO",      true  ],
            reset_maintenance:  ["Confirmer la révision ?",         "Le compteur d'entretien repartira sur un intervalle complet.",   "CONFIRMER LA RÉVISION", false ],
            end_trip:           ["Terminer le trajet ?",            "Le trajet sera clôturé et ses statistiques sauvegardées.",       "TERMINER LE TRAJET",   true  ],
            quit:               ["Quitter CliOS ?",                 "Les services seront arrêtés proprement avant la fermeture.",     "QUITTER",              true  ],
            restart:            ["Redémarrer CliOS ?",              "Les services seront relancés et le profil rechargé.",            "REDÉMARRER",           true  ],
            shutdown:           ["Éteindre le système ?",           "Le Raspberry Pi sera arrêté proprement.",                       "ÉTEINDRE",             true  ]
        }
        var d = copy[action]
        if (!d) return
        pendingAction = action
        pendingTitle  = d[0]
        pendingMsg    = d[1]
        pendingDanger = d[3]
        confirmDlg.acceptText = d[2]
        confirmDlg.open()
    }

    function executeConfirmed() {
        confirmDlg.close()
        switch (pendingAction) {
            case "reset_a":           bridge.resetTripA();          break
            case "reset_b":           bridge.resetTripB();          break
            case "reset_maintenance": bridge.resetMaintenance();    break
            case "end_trip":          bridge.endTripSession();      break
            case "quit":              bridge.quitApplication();     break
            case "restart":           bridge.restartApplication();  break
            case "shutdown":          bridge.shutdownSystem();      break
        }
        pendingAction = ""
    }

    // ── 1. Fond vivant Apex ───────────────────────────────────────────────────
    ApexAtmosphere {
        id: atmosphere
        anchors.fill: parent
        z: 0
    }

    // ── 2. Barre d'état supérieure ───────────────────────────────────────────
    ApexTopBar {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        z: 20
    }

    // ── 3. Zone de contenu principale (pleine hauteur) ───────────────────────
    Item {
        id: contentArea
        anchors {
            top:    topBar.bottom
            bottom: navBar.top
            left:   parent.left
            right:  parent.right
            topMargin:    6
            bottomMargin: 6
        }
        z: 5

        Loader {
            id: pageLoader
            anchors.fill: parent
            source: Qt.resolvedUrl("pages/ApexDrivePage.qml")

            // Transition de page
            opacity: 0
            NumberAnimation on opacity {
                id: fadeIn
                from: 0; to: 1; duration: 320; easing.type: Easing.OutCubic
            }

            onLoaded: {
                opacity = 0
                fadeIn.restart()
                // Connexion des signaux de navigation de la page chargée
            }
        }

        Connections {
            target: pageLoader.item
            ignoreUnknownSignals: true
            function onNavigateRequested(tgt) {
                // Pages secondaires (Apparence, Véhicule, etc.)
                var subPages = {
                    appearance: "../gt_modern/pages/GtAppearancePage.qml",
                    vehicle:    "../gt_modern/pages/GtVehiclePage.qml",
                    services:   "../gt_modern/pages/GtServicesPage.qml",
                    system:     "../gt_modern/pages/GtSystemPage.qml",
                    developer:  "../gt_modern/pages/GtDeveloperPage.qml"
                }
                if (subPages[tgt]) {
                    subPageLoader.source = Qt.resolvedUrl(subPages[tgt])
                    subPageOverlay.visible = true
                } else {
                    root.navigate(tgt)
                }
            }
            function onActionRequested(action) { root.askConfirmation(action) }
            function onBackRequested() {
                subPageOverlay.visible = false
                subPageLoader.source = ""
                root.navigate("menu")
            }
        }
    }

    // ── 5. Navigation tactile ─────────────────────────────────────────────────
    ApexNavBar {
        id: navBar
        anchors.bottom: parent.bottom
        anchors.left:   parent.left
        anchors.right:  parent.right
        current: root.currentTab
        z: 20
        onTabSelected: function(tabId) { root.navigate(tabId) }
    }

    // ── 6. Overlay pour sous-pages GT (Apparence, Véhicule...) ───────────────
    Rectangle {
        id: subPageOverlay
        anchors.fill: parent
        color: T.StyleManager.background
        visible: false
        z: 50

        Item {
            id: subPageArea
            anchors {
                fill: parent
                bottomMargin: navBar.height
            }

            Loader {
                id: subPageLoader
                anchors.fill: parent
            }

            Connections {
                target: subPageLoader.item
                ignoreUnknownSignals: true
                function onBackRequested() {
                    subPageOverlay.visible = false
                    subPageLoader.source = ""
                    root.navigate("menu")
                }
                function onNavigateRequested(tgt) { root.navigate(tgt) }
                function onActionRequested(action) { root.askConfirmation(action) }
            }
        }

        // NavBar visible aussi dans les sous-pages
        ApexNavBar {
            anchors.bottom: parent.bottom
            anchors.left:   parent.left
            anchors.right:  parent.right
            current: root.currentTab
            onTabSelected: function(tabId) {
                subPageOverlay.visible = false
                subPageLoader.source = ""
                root.navigate(tabId)
            }
        }
    }

    // ── 7. Overlay session (pause / fin trajet) ───────────────────────────────
    ApexSessionOverlay {
        id: sessionOverlay
        z: 100
        onActionRequested: function(action) { root.askConfirmation(action) }
    }

    // ── 8. Dialogue de confirmation ───────────────────────────────────────────
    ApexConfirmDialog {
        id: confirmDlg
        anchors.fill: parent
        z: 200
        title:      root.pendingTitle
        message:    root.pendingMsg
        dangerous:  root.pendingDanger
        onAccepted: root.executeConfirmed()
        onRejected: { close(); root.pendingAction = "" }
    }

    // ── 9. Bannière attention (interaction complexe) ──────────────────────────
    Rectangle {
        id: attentionBanner
        anchors.horizontalCenter: parent.horizontalCenter
        y: shown ? topBar.height + 10 : -60
        width: 400; height: 40; radius: 8
        color: "#FFB300"
        property bool shown: false
        z: 300

        Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

        Text {
            anchors.centerIn: parent
            text: "Interaction complexe — restez attentif"
            color: "#000000"
            font.pixelSize: 14; font.weight: Font.Bold
        }
    }

    Timer {
        id: attentionTimer; interval: 3000
        onTriggered: attentionBanner.shown = false
    }

    // Détection interaction complexe
    onCurrentTabChanged: {
        if (S.UiState.complexInteraction && currentTab !== "drive") {
            attentionBanner.shown = true
            attentionTimer.restart()
        }
    }
}
