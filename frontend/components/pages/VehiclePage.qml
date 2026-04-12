import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../style" as T

Item {
    id: root

    // --- Header ---
    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 20; leftMargin: 30 }
        height: 50

        Text {
            text: "VEHICULE"
            color: T.Theme.textMain
            font.pixelSize: 22; font.bold: true; font.letterSpacing: 2
        }
    }

    Column {
        anchors { top: header.bottom; left: parent.left; right: parent.right; margins: 30; topMargin: 40 }
        spacing: 15

        // --- BOUTON : PROFILS ---
        ButtonDelegate {
            title: "Profils & Véhicules"
            description: "Changer de voiture ou créer un nouveau profil"
            icon: "🚗"
            onClicked: root.StackView.view.push("VehicleProfiles.qml")
        }

        // --- BOUTON : STATS ---
        ButtonDelegate {
            title: "Coûts & Statistiques"
            description: "Prix du carburant et suivi de maintenance"
            icon: "⛽"
            onClicked: root.StackView.view.push("VehicleStats.qml")
        }
    }

    // --- Composant interne pour les boutons du menu ---
    component ButtonDelegate : Rectangle {
        property string title: ""
        property string description: ""
        property string icon: ""
        signal clicked()

        width: parent.width; height: 90
        color: ma.pressed ? T.Theme.main : T.Theme.bgDimmed
        radius: 12
        border.color: Qt.rgba(1, 1, 1, 0.05)

        Row {
            anchors { fill: parent; leftMargin: 20; rightMargin: 20 }
            spacing: 20
            verticalCenter: parent.verticalCenter

            Text { text: icon; font.pixelSize: 30; anchors.verticalCenter: parent.verticalCenter }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text { text: title; color: parent.parent.parent.ma.pressed ? T.Theme.bgMain : T.Theme.textMain; font.pixelSize: 18; font.bold: true }
                Text { text: description; color: parent.parent.parent.ma.pressed ? T.Theme.bgMain : T.Theme.unselected; font.pixelSize: 14 }
            }

            Text {
                text: "〉"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                color: parent.parent.parent.ma.pressed ? T.Theme.bgMain : T.Theme.unselected
                font.bold: true
            }
        }

        MouseArea { id: ma; anchors.fill: parent; onClicked: parent.clicked() }
    }
}