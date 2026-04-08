import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../style" as T

Item {
    id: root

    // ----------------------------------------------------
    // 1. HEADER STRICTEMENT ANCRÉ EN HAUT
    // ----------------------------------------------------
    Item {
        id: header
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            topMargin: 20
            leftMargin: 30
            rightMargin: 30
        }
        height: 50

        // Bouton Retour (Gauche)
        MouseArea {
            id: backBtn
            width: 150
            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
            }
            cursorShape: Qt.PointingHandCursor
            // Retourne automatiquement à la grille des paramètres
            onClicked: root.StackView.view.pop()

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Text {
                    text: "〈 "
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 26
                    font.bold: true
                    transform: Translate { x: backBtn.containsMouse ? -4 : 0 }
                    Behavior on transform { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                }
                Text {
                    text: "Retour"
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 20
                    font.bold: true
                }
            }
        }
    }

    // ----------------------------------------------------
    // 2. CONTENU CENTRAL (Chantier)
    // ----------------------------------------------------
    Column {
        anchors.centerIn: parent
        spacing: 20

        Text {
            text: "⚙️"
            font.pixelSize: 64
            anchors.horizontalCenter: parent.horizontalCenter
            opacity: 0.3
        }

        Text {
            text: "MODULE EN CONSTRUCTION"
            color: T.Theme.textMain
            font.pixelSize: 26
            font.bold: true
            font.letterSpacing: 2
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: "Cette fonctionnalité est en cours de développement\net sera disponible dans une prochaine mise à jour de CliOS."
            color: T.Theme.unselected
            font.pixelSize: 16
            horizontalAlignment: Text.AlignHCenter
            anchors.horizontalCenter: parent.horizontalCenter
            lineHeight: 1.3
        }
    }
}