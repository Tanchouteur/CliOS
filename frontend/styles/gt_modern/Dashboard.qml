import QtQuick
import QtQuick.Layouts
import "components"
import "pages"
import "../../style" as T
import "../../state" as S

Item {
    id: root
    objectName: "dashboardRoot"
    focus: true
    property string destination: "drive"
    property string previousDestination: "drive"
    property string confirmationAction: ""
    property string timeText: Qt.formatTime(new Date(), "hh:mm")

    readonly property var destinations: [
        { id: "drive", label: "CONDUITE", source: "pages/GtDrivePage.qml", complex: false },
        { id: "trip", label: "TRAJET", source: "pages/GtTripPage.qml", complex: true },
        { id: "performance", label: "PERFORMANCE", source: "pages/GtPerformancePage.qml", complex: true },
        { id: "diagnostic", label: "DIAGNOSTIC", source: "pages/GtDiagnosticPage.qml", complex: true },
        { id: "menu", label: "MENU", source: "pages/GtMenuPage.qml", complex: true }
    ]

    function routeInfo(id) {
        for (let i = 0; i < destinations.length; ++i)
            if (destinations[i].id === id) return destinations[i]
        const deep = {
            appearance: {id:"appearance", source:"../../shared_pages/AppearancePage.qml", complex:true},
            vehicle: {id:"vehicle", source:"../../shared_pages/VehiclePage.qml", complex:true},
            services: {id:"services", source:"../../shared_pages/ServicesPage.qml", complex:true},
            system: {id:"system", source:"../../shared_pages/SystemPage.qml", complex:true},
            developer: {id:"developer", source:"../../shared_pages/DeveloperPage.qml", complex:true}
        }
        return deep[id] || destinations[0]
    }

    function navigate(id) {
        const info = routeInfo(id)
        if (info.complex && S.UiState.complexInteraction) {
            attentionBanner.shown = true
            attentionTimer.restart()
        }
        previousDestination = destination
        destination = id
        pageLoader.source = Qt.resolvedUrl(info.source)
    }

    function askConfirmation(action) {
        if (action === "resume_trip") {
            bridge.resumeTripSession()
            return
        }
        confirmationAction = action
        const copy = {
            reset_a: ["Remettre Trip A à zéro ?", "La distance Trip A sera effacée.", "REMETTRE À ZÉRO", true],
            reset_b: ["Remettre Trip B à zéro ?", "La distance et la consommation Trip B seront effacées.", "REMETTRE À ZÉRO", true],
            reset_maintenance: ["Confirmer la révision ?", "Le compteur d’entretien repartira sur un intervalle complet.", "CONFIRMER LA RÉVISION", false],
            end_trip: ["Terminer le trajet ?", "Le trajet sera clôturé et ses statistiques sauvegardées.", "TERMINER LE TRAJET", true],
            quit: ["Quitter CliOS ?", "Les services seront arrêtés proprement avant la fermeture.", "QUITTER", true],
            restart: ["Redémarrer CliOS ?", "Les services seront relancés et le profil en attente sera chargé.", "REDÉMARRER", true],
            shutdown: ["Éteindre le système ?", "Le Raspberry Pi et les services CliOS seront arrêtés proprement.", "ÉTEINDRE", true]
        }
        const data = copy[action]
        if (!data) return
        confirmDialog.title = data[0]
        confirmDialog.message = data[1]
        confirmDialog.acceptText = data[2]
        confirmDialog.dangerous = data[3]
        confirmDialog.visible = true
    }

    function executeConfirmed() {
        confirmDialog.visible = false
        switch (confirmationAction) {
        case "reset_a": bridge.resetTripA(); break
        case "reset_b": bridge.resetTripB(); break
        case "reset_maintenance": bridge.resetMaintenance(); break
        case "end_trip": bridge.endTripSession(); break
        case "quit": bridge.quitApplication(); break
        case "restart": bridge.restartApplication(); break
        case "shutdown": bridge.shutdownSystem(); break
        }
        confirmationAction = ""
    }

    Keys.onPressed: event => {
        if (event.key === Qt.Key_T) {
            if (S.UiState.sessionState === "PAUSED") bridge.resumeTripSession()
            else bridge.setSessionState("PAUSED")
        }
    }

    Rectangle { anchors.fill: parent; color: T.StyleManager.background }

    // Barre d’état — 56 px.
    Rectangle {
        id: statusBar
        x: 0; y: 0; width: 1920; height: 56
        color: T.StyleManager.surface
        border.width: 0

        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18; spacing: 12
            Text { text: root.timeText; color: T.StyleManager.text; font.pixelSize: 25; font.weight: Font.DemiBold; Layout.preferredWidth: 76 }
            Text { text: S.UiState.fixed(S.UiState.outsideTemp, 1, "—") + " °C"; color: T.StyleManager.textSecondary; font.pixelSize: 19; Layout.preferredWidth: 90 }
            Rectangle { width: 1; Layout.fillHeight: true; Layout.topMargin: 12; Layout.bottomMargin: 12; color: T.StyleManager.outline }
            Row {
                Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; spacing: 7
                Repeater {
                    model: S.UiState.indicators
                    GtLamp { code: modelData.code; label: modelData.label; active: modelData.active; blinking: modelData.blink; lampColor: modelData.color }
                }
            }
            Rectangle {
                Layout.preferredWidth: 190; height: 38; radius: T.StyleManager.radiusSmall
                color: S.UiState.ramMode ? Qt.rgba(T.StyleManager.danger.r, T.StyleManager.danger.g, T.StyleManager.danger.b, 0.14) : Qt.rgba(T.StyleManager.success.r, T.StyleManager.success.g, T.StyleManager.success.b, 0.12)
                border.width: 1; border.color: S.UiState.ramMode ? T.StyleManager.danger : T.StyleManager.success
                Text { anchors.centerIn: parent; text: S.UiState.ramMode ? "USB · MODE RAM" : "USB · " + S.UiState.fixed(S.UiState.storageFreeMb, 0, "0") + " MB"; color: parent.border.color; font.pixelSize: 14; font.bold: true }
            }
            Rectangle {
                visible: S.UiState.serviceErrorKeys.length + S.UiState.serviceWarningKeys.length > 0
                Layout.preferredWidth: visible ? 170 : 0; height: 38; radius: T.StyleManager.radiusSmall
                color: Qt.rgba(T.StyleManager.warning.r, T.StyleManager.warning.g, T.StyleManager.warning.b, 0.13)
                border.width: 1; border.color: S.UiState.serviceErrorKeys.length ? T.StyleManager.danger : T.StyleManager.warning
                Text { anchors.centerIn: parent; text: S.UiState.serviceErrorKeys.length + " ERR · " + S.UiState.serviceWarningKeys.length + " AVIS"; color: parent.border.color; font.pixelSize: 14; font.bold: true }
            }
            Text { text: "CliOS GT"; color: T.StyleManager.accent; font.pixelSize: 20; font.weight: Font.Bold; Layout.preferredWidth: 95; horizontalAlignment: Text.AlignRight }
        }
    }

    // Panneau permanent conduite — 330 px.
    Rectangle {
        id: leftPanel
        x: 0; y: 56; width: 330; height: 580
        color: T.StyleManager.surface
        border.width: 1; border.color: T.StyleManager.outline
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 18; spacing: 12
            Text { text: "CONDUITE"; color: T.StyleManager.textSecondary; font.pixelSize: 17; font.weight: Font.DemiBold; font.letterSpacing: 1.5 }
            Column {
                Layout.fillWidth: true; Layout.preferredHeight: 160; spacing: -2
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: Math.round(S.UiState.speed); color: T.StyleManager.text; font.pixelSize: 112; font.weight: Font.DemiBold }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "km/h"; color: T.StyleManager.textSecondary; font.pixelSize: 21 }
            }
            GtCard {
                Layout.fillWidth: true; Layout.preferredHeight: 96; title: "Régulateur / limiteur"
                RowLayout {
                    anchors.fill: parent
                    Text { Layout.fillWidth: true; text: S.UiState.cruiseMode + " · " + S.UiState.cruiseStatus; color: T.StyleManager.textSecondary; font.pixelSize: 16; elide: Text.ElideRight }
                    Text { text: S.UiState.cruiseTarget > 0 ? Math.round(S.UiState.cruiseTarget) : "—"; color: T.StyleManager.accent; font.pixelSize: 30; font.weight: Font.DemiBold }
                }
            }
            GtCard {
                Layout.fillWidth: true; Layout.preferredHeight: 112; title: "Carburant"
                ColumnLayout {
                    anchors.fill: parent; spacing: 8
                    RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: S.UiState.fixed(S.UiState.fuelLevel, 1, "—") + " L"; color: S.UiState.lowFuel ? T.StyleManager.warning : T.StyleManager.text; font.pixelSize: 24; font.weight: Font.DemiBold } Text { text: S.UiState.fixed(S.UiState.autonomy, 0, "—") + " km"; color: T.StyleManager.textSecondary; font.pixelSize: 19 } }
                    GtProgress { Layout.fillWidth: true; height: 10; value: S.UiState.fuelLevel; to: S.UiState.maxFuel; fillColor: S.UiState.lowFuel ? T.StyleManager.warning : T.StyleManager.accent }
                }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                GtMetric { Layout.fillWidth: true; label: "Trip B"; value: S.UiState.fixed(S.UiState.tripB, 1, "0,0"); unit: "km"; valueSize: 27 }
                GtMetric { Layout.fillWidth: true; label: "Conso moy."; value: S.UiState.fixed(S.UiState.avgConsB, 1, "0,0"); unit: "L/100"; valueSize: 27 }
            }
        }
    }

    // Zone de contenu contextuel — 1260 px.
    Rectangle {
        x: 330; y: 56; width: 1260; height: 580
        color: T.StyleManager.background
        Loader {
            id: pageLoader
            anchors.fill: parent
            source: Qt.resolvedUrl("pages/GtDrivePage.qml")
        }
        Connections {
            target: pageLoader.item
            ignoreUnknownSignals: true
            function onNavigateRequested(target) { root.navigate(target) }
            function onBackRequested() { root.navigate("menu") }
            function onActionRequested(action) { root.askConfirmation(action) }
        }
        Rectangle {
            anchors.fill: parent
            visible: S.UiState.sessionState === "PAUSED" || S.UiState.sessionState === "ENDED"
            color: Qt.rgba(T.StyleManager.background.r, T.StyleManager.background.g, T.StyleManager.background.b, 0.91)
            GtCard {
                width: 900; height: 390; anchors.centerIn: parent
                title: S.UiState.sessionState === "ENDED" ? "Trajet terminé" : "Session en pause"
                highlighted: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 18
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 36
                        GtMetric { Layout.fillWidth: true; Layout.minimumWidth: 230; label: "Distance"; value: S.UiState.fixed(S.UiState.tripDistance, 1, "0,0"); unit: "km"; alignment: Text.AlignHCenter }
                        GtMetric { Layout.fillWidth: true; Layout.minimumWidth: 230; label: "Carburant"; value: S.UiState.fixed(S.UiState.tripFuelLiters, 2, "0,00"); unit: "L"; alignment: Text.AlignHCenter }
                        GtMetric { Layout.fillWidth: true; Layout.minimumWidth: 230; label: "Coût"; value: S.UiState.fixed(S.UiState.tripCost, 2, "0,00"); unit: "€"; alignment: Text.AlignHCenter }
                    }
                    Row {
                        visible: S.UiState.sessionState === "PAUSED"
                        Layout.alignment: Qt.AlignHCenter; spacing: 18
                        GtButton { width: 280; text: "CONTINUER"; primary: true; onClicked: bridge.resumeTripSession() }
                        GtButton { width: 320; text: "TERMINER LE TRAJET"; destructive: true; onClicked: root.askConfirmation("end_trip") }
                    }
                    Text { visible: S.UiState.sessionState === "ENDED"; Layout.alignment: Qt.AlignHCenter; text: "Données sauvegardées"; color: T.StyleManager.success; font.pixelSize: 24; font.weight: Font.DemiBold }
                }
            }
        }
    }

    // Panneau permanent moteur — 330 px.
    Rectangle {
        x: 1590; y: 56; width: 330; height: 580
        color: T.StyleManager.surface
        border.width: 1; border.color: T.StyleManager.outline
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 18; spacing: 12
            Text { text: "MOTEUR"; color: T.StyleManager.textSecondary; font.pixelSize: 17; font.weight: Font.DemiBold; font.letterSpacing: 1.5 }
            Column {
                Layout.fillWidth: true; Layout.preferredHeight: 150; spacing: -4
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.gear; color: S.UiState.redline ? T.StyleManager.danger : T.StyleManager.text; font.pixelSize: 72; font.weight: Font.Bold }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "RAPPORT"; color: T.StyleManager.textSecondary; font.pixelSize: 17 }
            }
            GtCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; title: "Régime moteur"; highlighted: S.UiState.redline
                ColumnLayout {
                    anchors.fill: parent; spacing: 10
                    RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: Math.round(S.UiState.rpm); color: S.UiState.redline ? T.StyleManager.danger : T.StyleManager.text; font.pixelSize: 36; font.weight: Font.DemiBold } Text { text: "tr/min"; color: T.StyleManager.textSecondary; font.pixelSize: 17 } }
                    GtProgress { Layout.fillWidth: true; height: 14; value: S.UiState.rpm; to: S.UiState.maxRpm; fillColor: S.UiState.redline ? T.StyleManager.danger : T.StyleManager.accent }
                    Text { text: "ZONE ROUGE  " + Math.round(S.UiState.redlineRpm); color: T.StyleManager.textSecondary; font.pixelSize: 14 }
                }
            }
            GtCard {
                Layout.fillWidth: true; Layout.preferredHeight: 134; title: "Température moteur"; highlighted: S.UiState.hotEngine
                ColumnLayout {
                    anchors.fill: parent; spacing: 10
                    RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: S.UiState.fixed(S.UiState.engineTemp, 0, "—"); color: S.UiState.hotEngine ? T.StyleManager.danger : T.StyleManager.text; font.pixelSize: 36; font.weight: Font.DemiBold } Text { text: "°C"; color: T.StyleManager.textSecondary; font.pixelSize: 18 } }
                    GtProgress { Layout.fillWidth: true; height: 12; value: S.UiState.engineTemp; from: 40; to: S.UiState.tempMax; fillColor: S.UiState.hotEngine ? T.StyleManager.danger : T.StyleManager.success }
                }
            }
            Text { Layout.fillWidth: true; Layout.fillHeight: true; text: S.UiState.hotEngine ? "TEMPÉRATURE CRITIQUE" : (S.UiState.redline ? "RÉGIME ÉLEVÉ" : "SYSTÈME MOTEUR NORMAL"); color: S.UiState.hotEngine || S.UiState.redline ? T.StyleManager.danger : T.StyleManager.success; font.pixelSize: 17; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
    }

    // Navigation tactile — 84 px.
    Rectangle {
        x: 0; y: 636; width: 1920; height: 84
        color: T.StyleManager.surfaceRaised
        border.width: 1; border.color: T.StyleManager.outline
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 240; anchors.rightMargin: 240; anchors.topMargin: 6; anchors.bottomMargin: 6; spacing: 16
            Repeater {
                model: root.destinations
                GtButton {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    text: modelData.label
                    primary: root.destination === modelData.id || (modelData.id === "menu" && ["appearance","vehicle","services","system","developer"].indexOf(root.destination) >= 0)
                    onClicked: root.navigate(modelData.id)
                }
            }
        }
    }

    GtAlertBanner {
        id: attentionBanner
        objectName: "attentionBanner"
        anchors.horizontalCenter: parent.horizontalCenter
        z: 800
        message: "Interaction complexe — restez attentif"
    }
    Timer { id: attentionTimer; interval: 3000; onTriggered: attentionBanner.shown = false }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.timeText = Qt.formatTime(new Date(), "hh:mm") }

    GtConfirmDialog {
        id: confirmDialog
        objectName: "confirmDialog"
        z: 1000
        onRejected: { visible = false; root.confirmationAction = "" }
        onAccepted: root.executeConfirmed()
    }
}
