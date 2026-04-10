import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Rectangle {
    id: root
    width: 160
    height: 55
    radius: 15
    color: Qt.rgba(0, 0, 0, 0.6)
    border.color: Qt.rgba(1, 1, 1, 0.1)
    border.width: 1

    property string displayDb: "0.0"
    property real numericDb: 0.0
    property int freqHz: 0

    function getFreqLabel(hz) {
        if (numericDb < 40.0 || hz === 0) return "Calme";
        if (hz < 80) return "Route / Grave";
        if (hz < 250) return "Moteur";
        if (hz < 2000) return "Voix / Médium";
        if (hz < 5000) return "Aigu";
        return "Sifflement";
    }

    Timer {
        interval: 100
        running: true
        repeat: true
        onTriggered: {
            if (bridge !== undefined && bridge.data !== undefined) {
                let dbStr = bridge.data["audio_db_text"];
                let freq = bridge.data["cabin_freq_hz"];

                if (dbStr !== undefined) {
                    root.displayDb = dbStr;
                    root.numericDb = Number(dbStr);
                }
                if (freq !== undefined) {
                    root.freqHz = freq;
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 12

        Text {
            text: "🔊"
            font.pixelSize: 20
            Layout.alignment: Qt.AlignVCenter
            transform: Translate {
                x: root.numericDb > 110 ? (Math.random() * 2 - 1) : 0
                y: root.numericDb > 110 ? (Math.random() * 2 - 1) : 0
            }
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: 0

            Text {
                text: root.displayDb + " dB"
                font.pixelSize: 16
                font.bold: true
                font.family: T.Theme.fontMono
                Layout.alignment: Qt.AlignLeft

                color: {
                    if (root.numericDb >= 110) return T.Theme.danger || "#ff0000";
                    if (root.numericDb >= 95)  return T.Theme.warning || "#ffaa00";
                    return T.Theme.textMain || "#ffffff";
                }
            }

            Text {
                text: root.freqHz
                font.pixelSize: 10
                color: T.Theme.unselected || "#aaaaaa" // Gris discret
                Layout.alignment: Qt.AlignLeft
            }
        }
    }
}