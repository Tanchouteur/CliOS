import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QC
import "components" as C
import "../style" as T
import "../state" as S

Item {
    id: root
    signal backRequested()

    property string view: S.UiState.bleScanning ? "scan" : "devices"
    property var selectedDevice: ({})
    property var selectedChar: ({})
    property var protocols: []
    property var predefinedNames: []
    property int protocolIndex: 0
    property string confirmedProtocol: ""
    property string chosenName: ""
    property string newGroupName: "Ambiance"
    readonly property var colorOptions: [
        { label: "Accent", value: "" }, { label: "Rouge", value: "#FF3030" },
        { label: "Vert", value: "#35D06F" }, { label: "Bleu", value: "#308CFF" },
        { label: "Ambre", value: "#FFAA22" }, { label: "Violet", value: "#A855F7" }
    ]

    Component.onCompleted: {
        protocols = bridge.getBleProtocols()
        predefinedNames = bridge.getLedPredefinedNames()
    }

    function beginConfiguration(device) {
        selectedDevice = device
        selectedChar = ({})
        protocolIndex = 0
        confirmedProtocol = ""
        chosenName = ""
        view = "wizard"
        bridge.requestBleCharacteristics(device.address)
    }

    function runProtocol(index) {
        if (!selectedChar.uuid || protocols.length === 0) return
        protocolIndex = Math.max(0, Math.min(index, protocols.length - 1))
        const protocol = protocols[protocolIndex]
        bridge.testBleProtocol(selectedDevice.address, selectedChar.uuid,
                               protocol.identifier, selectedChar.write_with_response === true)
    }

    function addConfirmedDevice() {
        if (!confirmedProtocol || !chosenName || !selectedChar.uuid) return
        if (bridge.addLedDevice(selectedDevice.address, chosenName, confirmedProtocol,
                                selectedChar.uuid, selectedChar.write_with_response === true,
                                selectedDevice.name || "")) {
            view = "devices"
        }
    }

    function colorIndex(value) {
        for (let i = 0; i < colorOptions.length; ++i)
            if (colorOptions[i].value === (value || "")) return i
        return 0
    }

    Rectangle { anchors.fill: parent; color: T.StyleManager.background }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 72
            color: T.StyleManager.surfaceRaised
            border.width: T.StyleManager.borderWidth; border.color: T.StyleManager.outline
            RowLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 16
                C.Button { Layout.preferredWidth: 190; Layout.preferredHeight: 48; text: "‹ MENU"; primary: true; onClicked: root.backRequested() }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 0
                    Text { text: "ÉCLAIRAGES BLE"; color: T.StyleManager.text; font.pixelSize: 23; font.bold: true; font.letterSpacing: 2 }
                    Text { text: "Jusqu'à " + S.UiState.ledMaxDevices + " contrôleurs • couleur d'accent par défaut"; color: T.StyleManager.textSecondary; font.pixelSize: 13 }
                }
                Text {
                    text: S.UiState.ledDevices.length + " / " + S.UiState.ledMaxDevices
                    color: S.UiState.ledDevices.length >= S.UiState.ledMaxDevices ? T.StyleManager.warning : T.StyleManager.success
                    font.pixelSize: 17; font.bold: true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 14; spacing: 14

            C.Card {
                Layout.preferredWidth: 350; Layout.fillHeight: true
                title: "GESTION"
                ColumnLayout {
                    anchors.fill: parent; spacing: 12
                    Text {
                        Layout.fillWidth: true
                        text: S.UiState.bleScanning ? "Recherche des appareils proches…" :
                              (S.UiState.ledDevices.length === 0 ? "Aucun éclairage configuré" : S.UiState.ledDevices.length + " éclairage(s) configuré(s)")
                        color: T.StyleManager.text; font.pixelSize: 19; font.bold: true; wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Les appareils suivent l'accent, sauf si une couleur est définie sur l'appareil ou son groupe."
                        color: T.StyleManager.textSecondary; font.pixelSize: 14; wrapMode: Text.WordWrap
                    }
                    Item { Layout.fillHeight: true }
                    C.Button {
                        Layout.fillWidth: true; Layout.preferredHeight: 64
                        text: S.UiState.bleScanning ? "ARRÊTER LE SCAN" : "SCANNER"
                        primary: !S.UiState.bleScanning
                        enabled: S.UiState.bleScanning || S.UiState.ledDevices.length < S.UiState.ledMaxDevices
                        onClicked: {
                            if (S.UiState.bleScanning) bridge.stopBleScan()
                            else { root.view = "scan"; bridge.requestBleScan() }
                        }
                    }
                    C.Button { Layout.fillWidth: true; Layout.preferredHeight: 56; text: "MES APPAREILS"; onClicked: root.view = "devices" }
                    C.Button { Layout.fillWidth: true; Layout.preferredHeight: 56; text: "GROUPES"; onClicked: root.view = "groups" }
                }
            }

            C.Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: root.view === "scan" ? "APPAREILS DÉTECTÉS" : (root.view === "wizard" ? "ASSISTANT DE CONFIGURATION" : (root.view === "groups" ? "GROUPES" : "MES ÉCLAIRAGES"))

                ListView {
                    anchors.fill: parent
                    visible: root.view === "devices"
                    clip: true; spacing: 10
                    model: S.UiState.ledDevices
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width; height: 118; radius: T.StyleManager.radiusMedium
                        color: T.StyleManager.surfaceRaised; border.width: 1; border.color: T.StyleManager.outline
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 14
                            Rectangle { width: 12; height: 12; radius: 6; color: modelData.health === "connected" ? T.StyleManager.success : (modelData.health === "error" ? T.StyleManager.danger : T.StyleManager.textSecondary) }
                            ColumnLayout {
                                Layout.preferredWidth: 275; spacing: 2
                                Text { text: modelData.name; color: T.StyleManager.text; font.pixelSize: 19; font.bold: true }
                                Text { text: modelData.protocol + " • " + modelData.ble_address; color: T.StyleManager.textSecondary; font.pixelSize: 12; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Text { text: modelData.color_override || "Suit la couleur d'accent"; color: modelData.color_override || T.StyleManager.accent; font.pixelSize: 12 }
                            }
                            QC.ComboBox {
                                Layout.preferredWidth: 128
                                model: root.colorOptions
                                textRole: "label"
                                currentIndex: root.colorIndex(modelData.color_override)
                                onActivated: index => bridge.updateLedDevice(modelData.id, "color_override", root.colorOptions[index].value)
                            }
                            C.Toggle {
                                checked: modelData.enabled
                                onToggled: checked => bridge.updateLedDevice(modelData.id, "enabled", checked ? "true" : "false")
                            }
                            QC.Slider {
                                Layout.fillWidth: true; from: 0; to: 100; value: modelData.brightness
                                onMoved: bridge.updateLedDevice(modelData.id, "brightness", String(value))
                            }
                            Text { text: Math.round(modelData.brightness) + "%"; color: T.StyleManager.text; font.pixelSize: 14; Layout.preferredWidth: 44 }
                            C.Button { Layout.preferredWidth: 128; Layout.preferredHeight: 54; text: "SUPPRIMER"; destructive: true; onClicked: bridge.removeLedDevice(modelData.id) }
                        }
                    }
                    Text { anchors.centerIn: parent; visible: parent.count === 0; text: "Aucun appareil. Lancez un scan pour commencer."; color: T.StyleManager.textSecondary; font.pixelSize: 18 }
                }

                ListView {
                    anchors.fill: parent
                    visible: root.view === "scan"
                    clip: true; spacing: 10
                    model: S.UiState.bleScanResults
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width; height: 92; radius: T.StyleManager.radiusMedium
                        color: T.StyleManager.surfaceRaised; border.width: 1; border.color: modelData.is_candidate ? T.StyleManager.accent : T.StyleManager.outline
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 14
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: modelData.name || "Appareil sans nom"; color: T.StyleManager.text; font.pixelSize: 19; font.bold: true }
                                Text { text: modelData.address + " • " + modelData.rssi + " dBm"; color: T.StyleManager.textSecondary; font.pixelSize: 13 }
                            }
                            Text { text: modelData.is_candidate ? "CONNU" : "BLE"; color: modelData.is_candidate ? T.StyleManager.success : T.StyleManager.textSecondary; font.bold: true }
                            C.Button { Layout.preferredWidth: 190; Layout.preferredHeight: 56; text: "CONFIGURER ›"; enabled: S.UiState.ledDevices.length < S.UiState.ledMaxDevices; onClicked: root.beginConfiguration(modelData) }
                        }
                    }
                    Text { anchors.centerIn: parent; visible: !S.UiState.bleScanning && parent.count === 0; text: "Aucun appareil détecté"; color: T.StyleManager.textSecondary; font.pixelSize: 18 }
                }

                ColumnLayout {
                    anchors.fill: parent; visible: root.view === "wizard"; spacing: 12
                    Text { text: selectedDevice.name || selectedDevice.address || "Appareil"; color: T.StyleManager.text; font.pixelSize: 22; font.bold: true }
                    Text { Layout.fillWidth: true; text: S.UiState.bleTestState.stage === "connecting" ? "Connexion et découverte GATT…" : "Choisissez la caractéristique, puis vérifiez visuellement chaque couleur témoin."; color: T.StyleManager.textSecondary; font.pixelSize: 14; wrapMode: Text.WordWrap }

                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 54; spacing: 8
                        Repeater {
                            model: S.UiState.bleCharacteristics
                            C.Button {
                                required property var modelData
                                Layout.fillWidth: true; Layout.fillHeight: true
                                text: modelData.uuid.substring(4, 8).toUpperCase() + (modelData.is_preferred ? " • CONSEILLÉ" : "")
                                primary: root.selectedChar.uuid === modelData.uuid
                                onClicked: root.selectedChar = modelData
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 120; radius: T.StyleManager.radiusMedium
                        color: T.StyleManager.surfaceRaised; border.width: 1; border.color: T.StyleManager.outline
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 14; spacing: 18
                            Rectangle { width: 74; height: 74; radius: 37; color: protocols.length ? protocols[protocolIndex].witness_color : T.StyleManager.surfaceSoft }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: protocols.length ? protocols[protocolIndex].identifier : "Aucun protocole"; color: T.StyleManager.text; font.pixelSize: 20; font.bold: true }
                                Text { text: protocols.length ? "Couleur attendue : " + protocols[protocolIndex].witness_name : ""; color: T.StyleManager.textSecondary; font.pixelSize: 14 }
                            }
                            C.Button { Layout.preferredWidth: 150; Layout.preferredHeight: 58; text: "TESTER"; primary: true; enabled: !!selectedChar.uuid && !S.UiState.bleTestState.running; onClicked: root.runProtocol(protocolIndex) }
                            C.Button { Layout.preferredWidth: 160; Layout.preferredHeight: 58; text: "C'EST BON"; enabled: !!selectedChar.uuid; onClicked: root.confirmedProtocol = protocols[protocolIndex].identifier }
                            C.Button { Layout.preferredWidth: 130; Layout.preferredHeight: 58; text: "SUIVANT"; enabled: protocols.length > 0; onClicked: { protocolIndex = (protocolIndex + 1) % protocols.length; root.runProtocol(protocolIndex) } }
                        }
                    }

                    QC.ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        visible: confirmedProtocol !== ""
                        GridLayout {
                            width: parent.width; columns: 3; rowSpacing: 8; columnSpacing: 8
                            Repeater {
                                model: predefinedNames
                                C.Button {
                                    required property var modelData
                                    Layout.fillWidth: true; Layout.preferredHeight: 50
                                    text: modelData; primary: chosenName === modelData
                                    onClicked: chosenName = modelData
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        C.Button { Layout.preferredWidth: 170; Layout.preferredHeight: 52; text: "ANNULER"; destructive: true; onClicked: { bridge.stopBleTest(); root.view = "scan" } }
                        Item { Layout.fillWidth: true }
                        C.Button { Layout.preferredWidth: 230; Layout.preferredHeight: 52; text: "AJOUTER"; primary: true; enabled: confirmedProtocol !== "" && chosenName !== ""; onClicked: root.addConfirmedDevice() }
                    }
                }

                ColumnLayout {
                    anchors.fill: parent; visible: root.view === "groups"; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        QC.TextField { Layout.fillWidth: true; text: root.newGroupName; placeholderText: "Nom du groupe"; onTextChanged: root.newGroupName = text }
                        C.Button { Layout.preferredWidth: 180; Layout.preferredHeight: 54; text: "CRÉER"; onClicked: bridge.addLedGroup(root.newGroupName) }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
                        model: S.UiState.ledGroups
                        delegate: Rectangle {
                            id: groupCard
                            required property var modelData
                            property var groupData: modelData
                            width: ListView.view.width; height: groupData.id === "all" ? 88 : 146; radius: T.StyleManager.radiusMedium
                            color: T.StyleManager.surfaceRaised; border.width: 1; border.color: T.StyleManager.outline
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 10; spacing: 6
                                RowLayout {
                                    Layout.fillWidth: true; Layout.preferredHeight: 62; spacing: 12
                                    ColumnLayout { Layout.preferredWidth: 210; Text { text: groupCard.groupData.name; color: T.StyleManager.text; font.pixelSize: 18; font.bold: true } Text { text: groupCard.groupData.device_count + " appareil(s)"; color: T.StyleManager.textSecondary; font.pixelSize: 12 } }
                                    C.Toggle { checked: groupCard.groupData.enabled; onToggled: checked => bridge.updateLedGroup(groupCard.groupData.id, "enabled", checked ? "true" : "false") }
                                    QC.Slider { Layout.fillWidth: true; from: 0; to: 100; value: groupCard.groupData.brightness; onMoved: bridge.updateLedGroup(groupCard.groupData.id, "brightness", String(value)) }
                                    QC.ComboBox {
                                        Layout.preferredWidth: 130; model: root.colorOptions; textRole: "label"
                                        currentIndex: root.colorIndex(groupCard.groupData.color_override)
                                        onActivated: index => bridge.updateLedGroup(groupCard.groupData.id, "color_override", root.colorOptions[index].value)
                                    }
                                    C.Button { Layout.preferredWidth: 130; Layout.preferredHeight: 52; text: "SUPPRIMER"; destructive: true; enabled: groupCard.groupData.id !== "all"; onClicked: bridge.removeLedGroup(groupCard.groupData.id) }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; Layout.preferredHeight: 48
                                    visible: groupCard.groupData.id !== "all"
                                    Text { text: "MEMBRES"; color: T.StyleManager.textSecondary; font.pixelSize: 12; font.bold: true }
                                    Repeater {
                                        model: S.UiState.ledDevices
                                        C.Button {
                                            required property var modelData
                                            property bool isMember: modelData.groups.indexOf(groupCard.groupData.id) >= 0
                                            Layout.fillWidth: true; Layout.preferredHeight: 42
                                            text: modelData.name; primary: isMember
                                            onClicked: bridge.setLedDeviceGroup(modelData.id, groupCard.groupData.id, !isMember)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Text { text: "L'appartenance aux groupes est conservée dans le catalogue. Le groupe Tout contient chaque nouvel appareil."; color: T.StyleManager.textSecondary; font.pixelSize: 13 }
                }
            }
        }
    }
}
