import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../style" as T
import "../components" as C

Item {
    id: root

    property var serviceKeys: (bridge !== undefined && bridge.systemHealth !== undefined) ? Object.keys(bridge.systemHealth) : []

    C.PageHeader {
        id: header
        title: "SERVICES"

        onBackClicked: {
            root.StackView.view.pop()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20
        anchors.topMargin: header.height + 50

        // --- LISTE GÉNÉRÉE AUTOMATIQUEMENT ---
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.serviceKeys
            spacing: 12
            clip: true

            delegate: Rectangle {
                id: serviceCard
                width: ListView.view.width

                // 🪄 L'ACCORDÉON : Hauteur dynamique si déplié
                height: isExpanded ? (80 + paramsLayout.implicitHeight + 20) : 80
                color: T.Theme.bgDimmed
                radius: 12
                border.color: cardMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.05)
                clip: true // Cache les paramètres quand c'est plié

                Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCirc } }

                property string serviceId: modelData
                property var srv: bridge.systemHealth[serviceId]
                property bool isOn: srv !== undefined && srv.status !== "DISABLED"

                // --- GESTION DES PARAMÈTRES (Le Caméléon) ---
                property var paramsList: []
                property bool isExpanded: false
                property bool hasParams: paramsList.length > 0

                // Demande les paramètres au Python quand la carte apparaît
                Component.onCompleted: {
                    if (bridge !== undefined) {
                        let pStr = bridge.getServiceParameters(serviceId);
                        if (pStr && pStr !== "[]") {
                            paramsList = JSON.parse(pStr);
                        }
                    }
                }

                // 1. LA ZONE D'EN-TÊTE (Toujours visible)
                Item {
                    width: parent.width
                    height: 80

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 20
                        anchors.rightMargin: 20
                        spacing: 15

                        Column {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 4

                            RowLayout {
                                spacing: 10
                                Text {
                                    text: serviceCard.serviceId
                                    color: serviceCard.isOn ? T.Theme.textMain : T.Theme.unselected
                                    font.pixelSize: 18; font.bold: true
                                }
                                // Affiche une flèche s'il y a des paramètres cachés
                                Text {
                                    visible: serviceCard.hasParams
                                    text: serviceCard.isExpanded ? "▼" : "▶"
                                    color: T.Theme.main
                                    font.pixelSize: 12
                                    Layout.alignment: Qt.AlignVCenter
                                }
                            }

                            Text {
                                text: serviceCard.srv !== undefined ? serviceCard.srv.message : "..."
                                color: serviceCard.isOn ? T.Theme.textDimmed : T.Theme.unselected
                                font.pixelSize: 12; wrapMode: Text.WordWrap; width: parent.width
                            }
                        }

                        // L'INTERRUPTEUR ON/OFF
                        Rectangle {
                            id: toggleTrack
                            width: 50; height: 28; radius: 14
                            color: serviceCard.isOn ? T.Theme.main : "#222222"
                            border.color: serviceCard.isOn ? T.Theme.main : "#444444"
                            Layout.alignment: Qt.AlignVCenter
                            Behavior on color { ColorAnimation { duration: 200 } }

                            Rectangle {
                                width: 24; height: 24; radius: 12; color: "#ffffff"; y: 2
                                x: serviceCard.isOn ? (toggleTrack.width - width - 2) : 2
                                Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }
                            }

                            // Ce clic est réservé UNIQUEMENT à l'allumage du service
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: bridge.toggleService(serviceCard.serviceId, !serviceCard.isOn)
                            }
                        }
                    }

                    // Ce clic étire la carte pour dévoiler les paramètres
                    MouseArea {
                        id: cardMouse
                        anchors.fill: parent
                        anchors.rightMargin: 60 // Évite de déborder sur l'interrupteur ON/OFF
                        hoverEnabled: true
                        cursorShape: serviceCard.hasParams ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (serviceCard.hasParams) {
                                serviceCard.isExpanded = !serviceCard.isExpanded;
                            }
                        }
                    }
                }

                // 2. LA ZONE CACHÉE (Les paramètres générés)
                ColumnLayout {
                    id: paramsLayout
                    y: 80 // Se place juste en dessous de l'en-tête
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    spacing: 15
                    opacity: serviceCard.isExpanded ? 1.0 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 200 } }

                    // Ligne de séparation
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1; color: Qt.rgba(1, 1, 1, 0.1)
                    }

                    Repeater {
                        model: serviceCard.paramsList
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            property var param: modelData

                            Text {
                                text: param.label
                                color: T.Theme.textDimmed || "#cccccc"
                                font.pixelSize: 14
                                Layout.preferredWidth: 160 // Largeur fixe pour aligner les sliders
                            }

                            // --- OPTION A : LE SLIDER ---
                            Slider {
                                visible: param.type === "slider"
                                Layout.fillWidth: true
                                from: param.min_val !== undefined ? param.min_val : 0
                                to: param.max_val !== undefined ? param.max_val : 100
                                value: param.value

                                // OnMoved s'active quand tu glisses (pas d'envoi inutile au démarrage)
                                onMoved: {
                                    bridge.setServiceParameter(serviceCard.serviceId, param.key, value)
                                    valText.text = Math.round(value) // Mise à jour de l'affichage
                                }
                            }
                            Text {
                                id: valText
                                visible: param.type === "slider"
                                text: Math.round(param.value)
                                color: T.Theme.textMain
                                font.pixelSize: 14
                                Layout.preferredWidth: 40
                                horizontalAlignment: Text.AlignRight
                            }

                            // --- OPTION B : LE MINI-TOGGLE ---
                            Rectangle {
                                visible: param.type === "toggle"
                                property bool isChecked: param.value // État local
                                width: 40; height: 22; radius: 11
                                color: isChecked ? T.Theme.main : "#333333"

                                Rectangle {
                                    width: 18; height: 18; radius: 9; color: "white"; y: 2
                                    x: parent.isChecked ? 20 : 2
                                    Behavior on x { NumberAnimation { duration: 150 } }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        parent.isChecked = !parent.isChecked;
                                        bridge.setServiceParameter(serviceCard.serviceId, param.key, parent.isChecked);
                                    }
                                }
                            }

                            // --- OPTION C : LA LISTE DÉROULANTE ---
                            ComboBox {
                                visible: param.type === "list"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 35
                                model: param.options !== undefined ? param.options : []

                                // On cherche la position de la valeur sauvegardée dans la liste
                                currentIndex: {
                                    if (param.options !== undefined) {
                                        let idx = param.options.indexOf(param.value);
                                        return Math.max(0, idx); // Si on ne trouve pas, on met 0 par défaut
                                    }
                                    return 0;
                                }

                                // Quand l'utilisateur sélectionne une nouvelle ligne
                                onActivated: {
                                    bridge.setServiceParameter(serviceCard.serviceId, param.key, currentValue)
                                }

                                // --- DESIGN DU BOUTON POUR COLLER AU THEME ---
                                background: Rectangle {
                                    color: "#222222"
                                    radius: 8
                                    border.color: parent.hovered ? T.Theme.main : "#444444"
                                    border.width: parent.hovered ? 2 : 1
                                    Behavior on border.color { ColorAnimation { duration: 150 } }}

                                contentItem: Text {
                                    text: parent.currentText
                                    color: T.Theme.textMain || "white"
                                    font.pixelSize: 14
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 15
                                }
                            }

                            // Pour pousser le toggle à gauche s'il n'y a pas de slider
                            Item {
                                visible: param.type !== "slider"
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }
    }
}