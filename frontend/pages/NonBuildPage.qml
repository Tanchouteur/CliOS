import QtQuick 2.15
import QtQuick.Controls 2.15
import "../style" as T
import "../components" as C

Item {
    id: root

    // ----------------------------------------------------
    // 1. HEADER STRICTEMENT ANCRÉ EN HAUT
    // ----------------------------------------------------
    C.PageHeader {
        id: header
        title: "En construction"

        onBackClicked: {
            root.StackView.view.pop()
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