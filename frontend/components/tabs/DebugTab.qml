import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import "../../style" as T

Item {
    id: root
    anchors.fill: parent

    ListModel {
        id: debugModel
    }

    // --- LE MOTEUR DE RAFRAICHISSEMENT---
    Timer {
        interval: 200
        running: true
        repeat: true
        onTriggered: {
            if (!bridge || bridge.data === undefined) return;

            let currentKeys = Object.keys(bridge.data).sort();

            if (currentKeys.length !== debugModel.count) {
                debugModel.clear();
                for (let i = 0; i < currentKeys.length; i++) {
                    let k = currentKeys[i];
                    let val = bridge.data[k];
                    let displayVal = typeof val === "number" ? Number(val).toFixed(3) : String(val);
                    debugModel.append({ "keyName": k, "keyValue": displayVal });
                }
            }

            else {
                for (let i = 0; i < currentKeys.length; i++) {
                    let k = currentKeys[i];
                    let val = bridge.data[k];
                    let displayVal = typeof val === "number" ? Number(val).toFixed(3) : String(val);

                    debugModel.setProperty(i, "keyValue", displayVal);
                }
            }
        }
    }

    // --- L'INTERFACE GRAPHIQUE ---
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        Text {
            text: "CONSOLE DE DÉBOGAGE CAN"
            color: T.Theme.textMain
            font.pixelSize: 22
            font.bold: true
            font.letterSpacing: 2
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Qt.rgba(1, 1, 1, 0.2)
        }

        // La liste défilante
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: debugModel
            clip: true
            spacing: 2

            delegate: Rectangle {
                width: ListView.view.width
                height: 35
                color: index % 2 === 0 ? Qt.rgba(1, 1, 1, 0.05) : "transparent"
                radius: 4

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10

                    Text {
                        text: keyName
                        color: T.Theme.textDimmed
                        font.pixelSize: 18
                        //font.family: "Monospace"
                        Layout.fillWidth: true
                    }

                    Text {
                        text: keyValue
                        color: T.Theme.mainLight
                        font.pixelSize: 20
                        font.bold: true
                        //font.family: "Monospace"
                        Layout.alignment: Qt.AlignRight
                    }
                }
            }
        }
    }
}