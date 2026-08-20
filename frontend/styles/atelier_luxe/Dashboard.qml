import QtQuick
import QtQuick.Layouts
import "../../style" as T
import "../../state" as S
import "./components"

Item {
    id: root
    objectName: "atelierLuxeDashboardRoot"
    signal settingsRequested(string route)
    signal commandRequested(string command)
    width: 1920
    height: 720
    clip: true

    // Propriété de pending action pour les dialogues de confirmation
    property string pendingAction: ""
    property string pendingTitle: ""
    property string pendingDescription: ""

    function handleAction(action) {
        root.commandRequested(action)
    }

    function executePendingAction() {
        root.commandRequested(pendingAction)
        pendingAction = ""
        confirmDialog.close()
    }

    // 1. Arrière-plan Vivant & Profondeur 3D (Micro-particules + Rayons 3D)
    LuxeAtmosphere {
        id: atmosphere
    }

    // 2. Couronne Supérieure Épurée (Statut flottant gravé)
    LuxeTopCrown {
        id: topCrown
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.right: parent.right
        onOpenSettingsRequested: root.settingsRequested("appearance")
    }

    // 3. Cluster Principal 1920×720 à Profondeur 3D
    RowLayout {
        id: clusterLayout
        anchors.top: topCrown.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 8
        anchors.bottomMargin: 14
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 12

        // Ailier Gauche Conducteur : Tachymètre 3D (480px)
        LuxeSpeedoChrono {
            id: speedo
            Layout.preferredWidth: 480
            Layout.fillHeight: true
        }

        // Cœur Central : Tourbillon Horloger Perpetuel & Grand Tourisme (880px)
        LuxeCenterCore {
            id: centerCore
            objectName: "centerCore"
            Layout.fillWidth: true
            Layout.fillHeight: true
            onActionRequested: function(action) { root.handleAction(action) }
        }

        // Ailier Droit Moteur : Compte-tours 3D (480px)
        LuxeTachoChrono {
            id: tacho
            Layout.preferredWidth: 480
            Layout.fillHeight: true
        }
    }

    // 4. Sous-pages éventuelles chargées par le bridge
    Loader {
        id: subPageLoader
        anchors.fill: parent
        visible: status === Loader.Ready && item !== null
        z: 700
    }

    // 6. Overlay Récapitulatif de Fin / Pause de Trajet
    LuxeSessionOverlay {
        id: sessionOverlay
        z: 900
        onActionRequested: function(action) { root.handleAction(action) }
    }

    // 7. Boîte de dialogue de Confirmation Universelle
    Item {
        id: confirmDialog
        anchors.fill: parent
        visible: opacity > 0.01
        opacity: 0.0
        Behavior on opacity { NumberAnimation { duration: 180 } }
        z: 1000

        function open() { opacity = 1.0 }
        function close() { opacity = 0.0 }

        Rectangle {
            anchors.fill: parent
            color: "#E604060A"
            MouseArea { anchors.fill: parent; onClicked: confirmDialog.close() }
        }

        Rectangle {
            anchors.centerIn: parent
            width: 580
            height: 280
            radius: 20
            color: "#0E1522"
            border.width: 2
            border.color: T.StyleManager.accent

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 16

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.pendingTitle
                    color: "#FFFFFF"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.Bold
                    font.letterSpacing: 1.5
                }

                Text {
                    Layout.fillWidth: true
                    text: root.pendingDescription
                    color: "#BAC8D9"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    Rectangle {
                        Layout.fillWidth: true; height: 50; radius: 12
                        color: "#182436"
                        border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.15)
                        Text { anchors.centerIn: parent; text: "ANNULER"; color: "#BAC8D9"; font.pixelSize: 14; font.bold: true }
                        MouseArea { anchors.fill: parent; onClicked: confirmDialog.close() }
                    }

                    Rectangle {
                        Layout.fillWidth: true; height: 50; radius: 12
                        color: T.StyleManager.accent
                        Text { anchors.centerIn: parent; text: "CONFIRMER"; color: "#000000"; font.pixelSize: 14; font.bold: true }
                        MouseArea { anchors.fill: parent; onClicked: root.executePendingAction() }
                    }
                }
            }
        }
    }
}
