import QtQuick
import QtQuick.Layouts
import "../../style" as T

Rectangle {
    id: root
    objectName: "tripRecoveryDialog"
    signal resumeRequested()
    signal newTripRequested()

    property bool available: false
    property int secondsRemaining: 0
    property var tripSummary: ({})

    visible: available
    anchors.fill: parent
    color: Qt.rgba(0.02, 0.03, 0.04, 0.97)

    function fixed(value, decimals) {
        const numeric = Number(value)
        return isNaN(numeric) ? "0" : numeric.toFixed(decimals).replace(".", ",")
    }

    function formattedDate(value) {
        const date = new Date(value || "")
        return isNaN(date.getTime()) ? "" : Qt.formatDateTime(date, "dd/MM/yyyy à hh:mm")
    }

    Rectangle {
        anchors.centerIn: parent
        width: 860
        height: 430
        radius: T.StyleManager.radiusLarge
        color: T.StyleManager.surface
        border.width: 2
        border.color: T.StyleManager.accent

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 38
            spacing: 22

            Text {
                Layout.fillWidth: true
                text: "CONTINUER LE TRAJET PRÉCÉDENT ?"
                color: T.StyleManager.text
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 31
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                text: "Le dernier trajet a été conservé lors de l’extinction."
                      + (root.formattedDate(root.tripSummary.date) !== ""
                         ? "\nDernier arrêt : " + root.formattedDate(root.tripSummary.date) : "")
                color: T.StyleManager.textSecondary
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 19
                horizontalAlignment: Text.AlignHCenter
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                spacing: 18

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.centerIn: parent
                        spacing: 7
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "DISTANCE"; color: T.StyleManager.textSecondary; font.pixelSize: 13; font.bold: true }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.fixed(root.tripSummary.distance_km, 1) + " km"; color: T.StyleManager.text; font.pixelSize: 30; font.bold: true }
                    }
                }
                Rectangle { width: 1; Layout.fillHeight: true; color: T.StyleManager.outline }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.centerIn: parent
                        spacing: 7
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "COÛT ESTIMÉ"; color: T.StyleManager.textSecondary; font.pixelSize: 13; font.bold: true }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.fixed(root.tripSummary.cost_eur, 2) + " €"; color: T.StyleManager.text; font.pixelSize: 30; font.bold: true }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: "Nouveau trajet automatique dans " + root.secondsRemaining + " s"
                color: T.StyleManager.warning
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 17
                font.weight: Font.Bold
                horizontalAlignment: Text.AlignHCenter
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 18
                Button {
                    Layout.preferredWidth: 300
                    text: "NOUVEAU TRAJET"
                    onClicked: root.newTripRequested()
                }
                Button {
                    Layout.preferredWidth: 350
                    text: "CONTINUER LE TRAJET"
                    primary: true
                    onClicked: root.resumeRequested()
                }
            }
        }
    }
}
