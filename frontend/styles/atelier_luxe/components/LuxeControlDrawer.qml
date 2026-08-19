import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 1920
    height: 720
    anchors.fill: parent
    visible: opacity > 0.01
    opacity: 0.0
    Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

    signal closeRequested()
    signal actionRequested(string action)

    property int activeTab: 0 // 0: Apparence, 1: Services & Carburant, 2: Véhicule & Système

    readonly property var luxuryAccents: [
        { name: "Or Champagne", code: "#D4AF37" },
        { name: "Platine Cyan", code: "#48B8FF" },
        { name: "Émeraude GT", code: "#38D996" },
        { name: "Bronze Ambré", code: "#FFB33B" },
        { name: "Rouge Rubis", code: "#FF5A67" },
        { name: "Nacre Pure", code: "#F4F7FA" }
    ]

    readonly property var serviceKeys: Object.keys(S.UiState.serviceHealth)

    function adjustFuelPrice(delta) {
        const current = S.UiState.number(S.UiState.fuelPrice, 1.70)
        const next = Math.max(0.50, Math.min(3.50, Math.round((current + delta) * 100) / 100))
        bridge.updateFuelPrice(next)
    }

    function setFuelPrice(price) {
        bridge.updateFuelPrice(price)
    }

    function open() {
        opacity = 1.0
    }

    function close() {
        opacity = 0.0
        root.closeRequested()
    }

    // Fond sombre translucide (Backdrop)
    Rectangle {
        anchors.fill: parent
        color: "#F004060A" // 94% noir
        MouseArea { anchors.fill: parent; onClicked: root.close() }
    }

    // Panneau de contrôle central de prestige (1380 x 620 px)
    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: 1380
        height: 620
        radius: 20
        color: "#0B111A"
        border.width: 1.5
        border.color: "#1E2C3E"

        // Empêche la propagation du clic
        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            // =================================================================
            // 1. EN-TÊTE DU PANNEAU AVEC SÉLECTEUR D'ONGLETS
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Column {
                    spacing: 2
                    Text {
                        text: "CENTRE DE CONTRÔLE"
                        color: "#FFFFFF"
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 20
                        font.weight: Font.Bold
                        font.letterSpacing: 1.5
                    }
                    Text {
                        text: "Paramètres, services et personnalisation CliOS"
                        color: "#8A9BAF"
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 12
                    }
                }

                Item { Layout.fillWidth: true }

                // Sélecteur d'onglets
                RowLayout {
                    spacing: 8

                    Repeater {
                        model: [
                            { id: 0, title: "APPARENCE & STYLES" },
                            { id: 1, title: "SERVICES & CARBURANT" },
                            { id: 2, title: "ACTIONS & SYSTÈME" }
                        ]

                        Rectangle {
                            width: 190
                            height: 38
                            radius: 19
                            property bool isSelected: root.activeTab === modelData.id
                            color: isSelected ? Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.22) : "#101826"
                            border.width: 1.2
                            border.color: isSelected ? T.StyleManager.accent : "#1E2C3E"

                            Text {
                                anchors.centerIn: parent
                                text: modelData.title
                                color: isSelected ? "#FFFFFF" : "#8A9BAF"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                font.letterSpacing: 0.8
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.activeTab = modelData.id
                            }
                        }
                    }
                }

                // Bouton Fermer (X)
                Rectangle {
                    width: 38
                    height: 38
                    radius: 19
                    color: "#182436"
                    border.width: 1
                    border.color: "#2C3F58"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: "#FFFFFF"
                        font.pixelSize: 15
                        font.weight: Font.Bold
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: "#182436" }

            // =================================================================
            // 2. CONTENU PAR ONGLET
            // =================================================================
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // -------------------------------------------------------------
                // ONGLET 0 : APPARENCE & STYLES
                // -------------------------------------------------------------
                RowLayout {
                    anchors.fill: parent
                    visible: root.activeTab === 0
                    spacing: 16

                    // Nuancier de couleurs d'accent
                    Rectangle {
                        Layout.preferredWidth: 420
                        Layout.fillHeight: true
                        radius: 14
                        color: "#0E1624"
                        border.width: 1
                        border.color: "#182436"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 14

                            Text {
                                text: "COULEUR D'ACCENTUATION"
                                color: T.StyleManager.accent
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            Text {
                                text: "Sélectionnez l'ambiance lumineuse appliquée aux aiguilles, cadrans et données vitales."
                                color: "#8A9BAF"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            GridLayout {
                                Layout.alignment: Qt.AlignHCenter
                                columns: 3
                                columnSpacing: 16
                                rowSpacing: 16

                                Repeater {
                                    model: root.luxuryAccents

                                    Column {
                                        spacing: 6
                                        Rectangle {
                                            width: 80
                                            height: 80
                                            radius: 40
                                            color: modelData.code
                                            property bool isCurrent: String(T.StyleManager.rawAccent).toLowerCase() === String(modelData.code).toLowerCase()
                                            border.width: isCurrent ? 4 : 2
                                            border.color: isCurrent ? "#FFFFFF" : Qt.rgba(1, 1, 1, 0.2)

                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: bridge.save_setting("theme.main", String(modelData.code))
                                            }
                                        }

                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: modelData.name
                                            color: "#BAC8D9"
                                            font.family: T.StyleManager.fontFamily
                                            font.pixelSize: 11
                                            font.weight: Font.Bold
                                        }
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }

                    // Sélecteur de styles du tableau de bord (Défilement fluide ListView)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 14
                        color: "#0E1624"
                        border.width: 1
                        border.color: "#182436"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "STYLES DU TABLEAU DE BORD"
                                    color: "#BAC8D9"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 12
                                    font.weight: Font.Bold
                                    font.letterSpacing: 1.2
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: "Faites glisser pour explorer"
                                    color: "#8A9BAF"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 11
                                }
                            }

                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                orientation: ListView.Horizontal
                                spacing: 14
                                clip: true
                                boundsBehavior: Flickable.DragAndOvershootBounds
                                model: T.StyleManager.styles

                                delegate: Rectangle {
                                    width: 250
                                    height: ListView.view.height
                                    radius: 12
                                    property bool isCurrent: T.StyleManager.styleId === modelData.id
                                    color: isCurrent ? Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.18) : "#080D15"
                                    border.width: isCurrent ? 2 : 1
                                    border.color: isCurrent ? T.StyleManager.accent : "#182436"

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 10

                                        Text {
                                            text: modelData.label
                                            color: "#FFFFFF"
                                            font.family: T.StyleManager.fontFamily
                                            font.pixelSize: 17
                                            font.weight: Font.Bold
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.description
                                            color: "#BAC8D9"
                                            font.family: T.StyleManager.fontFamily
                                            font.pixelSize: 12
                                            wrapMode: Text.WordWrap
                                            elide: Text.ElideRight
                                            maximumLineCount: 3
                                        }

                                        Item { Layout.fillHeight: true }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: 44
                                            radius: 8
                                            color: isCurrent ? T.StyleManager.accent : "#182436"

                                            Text {
                                                anchors.centerIn: parent
                                                text: isCurrent ? "STYLE ACTIF" : "CHOISIR"
                                                color: isCurrent ? "#000000" : "#FFFFFF"
                                                font.pixelSize: 13
                                                font.weight: Font.Bold
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: T.StyleManager.selectStyle(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // ONGLET 1 : SERVICES SYSTÈME & PRIX DU CARBURANT
                // -------------------------------------------------------------
                RowLayout {
                    anchors.fill: parent
                    visible: root.activeTab === 1
                    spacing: 16

                    // Réglage du Prix du Carburant (€/L)
                    Rectangle {
                        Layout.preferredWidth: 460
                        Layout.fillHeight: true
                        radius: 14
                        color: "#0E1624"
                        border.width: 1
                        border.color: "#182436"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "PRIX DU CARBURANT (€ / L)"
                                color: T.StyleManager.accent
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            Text {
                                text: "Utilisé pour estimer avec précision le coût financier réel de chaque trajet."
                                color: "#8A9BAF"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            // Affichage central du prix actuel
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 100
                                radius: 12
                                color: "#080D15"
                                border.width: 1.5
                                border.color: "#182436"

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 8
                                    Text {
                                        text: S.UiState.fixed(S.UiState.fuelPrice, 2, "1,70")
                                        color: "#FFFFFF"
                                        font.family: T.StyleManager.fontFamily
                                        font.pixelSize: 48
                                        font.weight: Font.Bold
                                    }
                                    Text {
                                        text: "€ / L"
                                        color: T.StyleManager.accent
                                        font.family: T.StyleManager.fontFamily
                                        font.pixelSize: 22
                                        font.weight: Font.Bold
                                    }
                                }
                            }

                            // Boutons d'ajustement fin
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Rectangle {
                                    Layout.fillWidth: true; height: 48; radius: 8; color: "#182436"; border.width: 1; border.color: "#2C3F58"
                                    Text { anchors.centerIn: parent; text: "- 0.10"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                    MouseArea { anchors.fill: parent; onClicked: root.adjustFuelPrice(-0.10) }
                                }
                                Rectangle {
                                    Layout.fillWidth: true; height: 48; radius: 8; color: "#182436"; border.width: 1; border.color: "#2C3F58"
                                    Text { anchors.centerIn: parent; text: "- 0.01"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                    MouseArea { anchors.fill: parent; onClicked: root.adjustFuelPrice(-0.01) }
                                }
                                Rectangle {
                                    Layout.fillWidth: true; height: 48; radius: 8; color: "#182436"; border.width: 1; border.color: "#2C3F58"
                                    Text { anchors.centerIn: parent; text: "+ 0.01"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                    MouseArea { anchors.fill: parent; onClicked: root.adjustFuelPrice(0.01) }
                                }
                                Rectangle {
                                    Layout.fillWidth: true; height: 48; radius: 8; color: "#182436"; border.width: 1; border.color: "#2C3F58"
                                    Text { anchors.centerIn: parent; text: "+ 0.10"; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true }
                                    MouseArea { anchors.fill: parent; onClicked: root.adjustFuelPrice(0.10) }
                                }
                            }

                            // Boutons Pré-réglages rapides
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Repeater {
                                    model: [1.60, 1.70, 1.80, 1.90, 2.00]
                                    Rectangle {
                                        Layout.fillWidth: true
                                        height: 38
                                        radius: 6
                                        color: Math.abs(S.UiState.number(S.UiState.fuelPrice, 1.70) - modelData) < 0.005 ? T.StyleManager.accent : "#121A28"
                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.toFixed(2) + " €"
                                            color: Math.abs(S.UiState.number(S.UiState.fuelPrice, 1.70) - modelData) < 0.005 ? "#000000" : "#BAC8D9"
                                            font.pixelSize: 12
                                            font.bold: true
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: root.setFuelPrice(modelData)
                                        }
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }

                    // Liste & Contrôle des Services Système
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 14
                        color: "#0E1624"
                        border.width: 1
                        border.color: "#182436"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "SERVICES & MODULES SYSTÈME"
                                    color: "#BAC8D9"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 12
                                    font.weight: Font.Bold
                                    font.letterSpacing: 1.2
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: root.serviceKeys.length + " services supervisés"
                                    color: "#8A9BAF"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 11
                                }
                            }

                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 8
                                clip: true
                                model: root.serviceKeys

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 64
                                    radius: 10
                                    color: "#080D15"
                                    border.width: 1
                                    border.color: "#182436"

                                    property string serviceId: String(modelData)
                                    property var details: S.UiState.serviceHealth[serviceId] || ({})
                                    property bool isRunning: details.status !== "DISABLED"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        spacing: 14

                                        // Voyant d'état lumineux
                                        Rectangle {
                                            width: 12
                                            height: 12
                                            radius: 6
                                            color: details.status === "ERROR" ? T.StyleManager.danger :
                                                   details.status === "WARNING" ? T.StyleManager.warning :
                                                   isRunning ? T.StyleManager.success : "#4A5B6E"
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2
                                            Text {
                                                text: serviceId
                                                color: "#FFFFFF"
                                                font.family: T.StyleManager.fontFamily
                                                font.pixelSize: 15
                                                font.weight: Font.Bold
                                            }
                                            Text {
                                                text: details.message || details.status || "Statut normal"
                                                color: "#8A9BAF"
                                                font.family: T.StyleManager.fontFamily
                                                font.pixelSize: 11
                                                elide: Text.ElideRight
                                            }
                                        }

                                        // Bouton Interrupteur Toggle (ON / OFF)
                                        Rectangle {
                                            width: 80
                                            height: 36
                                            radius: 18
                                            color: isRunning ? Qt.rgba(T.StyleManager.success.r, T.StyleManager.success.g, T.StyleManager.success.b, 0.25) : "#141C28"
                                            border.width: 1.2
                                            border.color: isRunning ? T.StyleManager.success : "#2C3F58"

                                            RowLayout {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                Rectangle {
                                                    width: 8; height: 8; radius: 4
                                                    color: isRunning ? T.StyleManager.success : "#8A9BAF"
                                                }
                                                Text {
                                                    text: isRunning ? "ACTIF" : "ARRÊT"
                                                    color: isRunning ? "#FFFFFF" : "#8A9BAF"
                                                    font.family: T.StyleManager.fontFamily
                                                    font.pixelSize: 11
                                                    font.weight: Font.Bold
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: bridge.toggleService(serviceId, !isRunning)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // ONGLET 2 : ACTIONS VÉHICULE & COMMANDES SYSTÈME
                // -------------------------------------------------------------
                RowLayout {
                    anchors.fill: parent
                    visible: root.activeTab === 2
                    spacing: 16

                    // Actions Trajet & Maintenance
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 14
                        color: "#0E1624"
                        border.width: 1
                        border.color: "#182436"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "ACTIONS DU TRAJET & ENTRETIEN"
                                color: T.StyleManager.accent
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 52
                                    radius: 10
                                    color: "#182436"
                                    border.width: 1
                                    border.color: "#2C3F58"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Remise à 0 Trip A"
                                        color: "#FFFFFF"
                                        font.family: T.StyleManager.fontFamily
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.actionRequested("reset_a")
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 52
                                    radius: 10
                                    color: "#182436"
                                    border.width: 1
                                    border.color: "#2C3F58"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Remise à 0 Trip B"
                                        color: "#FFFFFF"
                                        font.family: T.StyleManager.fontFamily
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.actionRequested("reset_b")
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 52
                                radius: 10
                                color: "#182436"
                                border.width: 1
                                border.color: "#2C3F58"

                                Text {
                                    anchors.centerIn: parent
                                    text: "Valider Révision / Entretien Effectué"
                                    color: "#FFFFFF"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 14
                                    font.weight: Font.Bold
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: root.actionRequested("maintenance")
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }

                    // Commandes d'Alimentation
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 14
                        color: "#0E1624"
                        border.width: 1
                        border.color: "#182436"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "ALIMENTATION & SYSTÈME"
                                color: "#BAC8D9"
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                font.letterSpacing: 1.2
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 54
                                    radius: 10
                                    color: Qt.rgba(T.StyleManager.warning.r, T.StyleManager.warning.g, T.StyleManager.warning.b, 0.22)
                                    border.width: 1.2
                                    border.color: T.StyleManager.warning

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Redémarrer CliOS"
                                        color: "#FFFFFF"
                                        font.family: T.StyleManager.fontFamily
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.actionRequested("restart")
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 54
                                    radius: 10
                                    color: Qt.rgba(T.StyleManager.danger.r, T.StyleManager.danger.g, T.StyleManager.danger.b, 0.22)
                                    border.width: 1.2
                                    border.color: T.StyleManager.danger

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Éteindre Système"
                                        color: "#FFFFFF"
                                        font.family: T.StyleManager.fontFamily
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.actionRequested("shutdown")
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 50
                                radius: 10
                                color: "#182436"
                                border.width: 1
                                border.color: "#2C3F58"

                                Text {
                                    anchors.centerIn: parent
                                    text: "Quitter vers le Bureau"
                                    color: "#BAC8D9"
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: root.actionRequested("quit")
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }
    }
}
