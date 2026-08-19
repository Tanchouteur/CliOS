import QtQuick
import "components"
import "pages"
import "../../style"
import "../../state" as S

Item {
    id: root
    objectName: "legacyDashboardRoot"
    property string sessionState: S.UiState.sessionState

    Rectangle { anchors.fill: parent; color: "#000000" }

    StatusBar {
        anchors.top: parent.top
        anchors.left: parent.left
    }

    SplMeterWidget {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 20
        anchors.rightMargin: 20
        z: 100
    }

    Item {
        id: centerGroup
        width: 960
        height: 630
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -30
        z: 10

        CenterHub { anchors.fill: parent }

        Image {
            source: "../../assets/Renault-Logo-w.png"
            anchors.centerIn: parent
            width: 240
            fillMode: Image.PreserveAspectFit
        }

        CarStatusWidget { anchors.centerIn: parent }
    }

    Item {
        width: 500
        height: 450
        anchors.left: parent.left
        anchors.leftMargin: -28
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 50

        SpeedometerBmw {
            width: 500
            height: 400
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            scale: 1.15
        }
    }

    Item {
        width: 500
        height: 400
        anchors.right: parent.right
        anchors.rightMargin: -28
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 50

        TachometerBmw {
            width: 500
            height: 400
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            scale: 1.15
        }
    }

    Rectangle {
        visible: root.sessionState === "PAUSED" || root.sessionState === "ENDED"
        anchors.fill: parent
        z: 500
        color: Qt.rgba(0, 0, 0, 0.91)

        Rectangle {
            width: 760
            height: 350
            anchors.centerIn: parent
            radius: 20
            color: "#151515"
            border.width: 2
            border.color: Theme.main

            Column {
                anchors.centerIn: parent
                spacing: 30

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.sessionState === "ENDED" ? "Trajet terminé" : "Résumé du trajet"
                    color: "white"
                    font.family: "Arial"
                    font.pixelSize: 34
                    font.bold: true
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 55
                    LegacyMetric { label: "Distance"; value: S.UiState.tripDistance.toFixed(1) + " km" }
                    LegacyMetric { label: "Carburant"; value: S.UiState.tripFuelLiters.toFixed(2) + " L" }
                    LegacyMetric { label: "Coût"; value: S.UiState.tripCost.toFixed(2) + " €" }
                }

                Row {
                    visible: root.sessionState === "PAUSED"
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 20
                    LegacyButton { text: "CONTINUER"; onClicked: bridge.resumeTripSession() }
                    LegacyButton { text: "TERMINER"; dangerous: true; onClicked: bridge.endTripSession() }
                }
            }
        }
    }

    Item {
        id: bottomBar
        width: parent.width * 0.90
        height: 42
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        property string timeText: Qt.formatTime(new Date(), "hh:mm")

        Timer { interval: 1000; running: true; repeat: true; onTriggered: bottomBar.timeText = Qt.formatTime(new Date(), "hh:mm") }

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "Autonomie  " + S.UiState.autonomy.toFixed(0) + " km"
            color: "white"
            font.family: "Arial"
            font.pixelSize: 22
        }
        Text {
            anchors.centerIn: parent
            text: bottomBar.timeText + "     " + S.UiState.odometer.toFixed(0) + " km"
            color: "white"
            font.family: "Arial"
            font.pixelSize: 22
        }
        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: S.UiState.outsideTemp.toFixed(1) + " °C"
            color: "white"
            font.family: "Arial"
            font.pixelSize: 22
        }
    }

    Rectangle {
        width: 224
        height: 58
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 16
        anchors.bottomMargin: 10
        z: 1000
        radius: 10
        color: "#202020"
        border.width: 2
        border.color: Theme.main

        Text {
            anchors.centerIn: parent
            text: "RETOUR AUX STYLES GT"
            color: "white"
            font.family: "Arial"
            font.pixelSize: 16
            font.bold: true
        }
        MouseArea { anchors.fill: parent; onClicked: StyleManager.selectStyle("gt_modern") }
    }

    component LegacyMetric: Column {
        property string label: ""
        property string value: ""
        spacing: 5
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: parent.label; color: Theme.textDimmed; font.family: "Arial"; font.pixelSize: 16 }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: parent.value; color: "white"; font.family: "Arial"; font.pixelSize: 27; font.bold: true }
    }

    component LegacyButton: Rectangle {
        signal clicked()
        property string text: "ACTION"
        property bool dangerous: false
        width: 245
        height: 64
        radius: 10
        color: "#252525"
        border.width: 2
        border.color: dangerous ? Theme.danger : Theme.main
        Text { anchors.centerIn: parent; text: parent.text; color: "white"; font.family: "Arial"; font.pixelSize: 18; font.bold: true }
        MouseArea { anchors.fill: parent; onClicked: parent.clicked() }
    }
}
