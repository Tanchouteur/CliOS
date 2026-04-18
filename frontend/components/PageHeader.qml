import QtQuick 2.15
import QtQuick.Controls 2.15
import "../style" as T

Item {
    id: root

    property string title: "TITRE"

    // --- NOUVEAU : Le signal qui prévient la page parente ---
    signal backClicked()

    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.leftMargin: 30
    anchors.rightMargin: 30
    anchors.topMargin: 20

    height: 70

    // Zone de retour (Bouton)
    Rectangle {
        id: backArea
        width: 180
        height: parent.height
        radius: 12

        // UX : Feedback visuel au clic (fond coloré)
        color: backBtn.pressed ? Qt.rgba(T.Theme.main.r, T.Theme.main.g, T.Theme.main.b, 0.15) : "transparent"
        // UX : Contour fin pour identifier que c'est un bouton
        border.color: Qt.rgba(T.Theme.main.r, T.Theme.main.g, T.Theme.main.b, 0.6)
        border.width: 1

        Row {
            anchors.centerIn: parent
            spacing: 15

            Text {
                text: "〈"
                color: T.Theme.textMain
                font.pixelSize: 32
                font.bold: true
                // UX : Le chevron recule quand on appuie
                x: backBtn.pressed ? -6 : 0
                Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            }

            Text {
                text: "Retour"
                color: T.Theme.textMain
                font.pixelSize: 22
                font.bold: true
            }
        }

        MouseArea {
            id: backBtn
            anchors.fill: parent
            // --- CORRECTION : On déclenche le signal ---
            onClicked: root.backClicked()
        }
    }

    // Titre
    Text {
        anchors.centerIn: parent
        text: root.title
        color: T.Theme.textMain
        font.pixelSize: 24
        font.bold: true
        font.letterSpacing: 2
    }
}