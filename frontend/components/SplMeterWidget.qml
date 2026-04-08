import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Rectangle {
    id: root
    width: 130
    height: 50
    radius: 25
    color: Qt.rgba(0, 0, 0, 0.6)
    border.color: Qt.rgba(1, 1, 1, 0.1)
    border.width: 1

    property string displayDb: "0.0"
    property real numericDb: 0.0

    Timer {
        interval: 100
        running: true
        repeat: true
        onTriggered: {
            if (bridge !== undefined && bridge.data !== undefined) {
                // On va chercher notre beau TEXTE
                let dbStr = bridge.data["audio_db_text"];

                if (dbStr !== undefined) {
                    root.displayDb = dbStr;
                    root.numericDb = Number(dbStr);
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 10

        Text {
            text: "🔊"
            font.pixelSize: 18
            Layout.alignment: Qt.AlignVCenter
            transform: Translate {
                x: root.numericDb > 110 ? (Math.random() * 2 - 1) : 0
                y: root.numericDb > 110 ? (Math.random() * 2 - 1) : 0
            }
        }

        Text {
            // On affiche directement le texte fourni par Python
            text: root.displayDb + " dB"
            font.pixelSize: 18
            font.bold: true
            //font.family: "Monospace"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight

            color: {
                if (root.numericDb >= 110) return T.Theme.danger;
                if (root.numericDb >= 95)  return T.Theme.warning;
                return T.Theme.textMain;
            }
        }
    }
}