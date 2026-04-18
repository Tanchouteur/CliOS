import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T
import "../components" as C

Item {
    id: root
    property string logsText: ""
    property string bundlePath: ""

    // ----------------------------------------------------
    // 1. HEADER STRICTEMENT ANCRÉ EN HAUT
    // ----------------------------------------------------
    C.PageHeader {
        id: header
        title: "JOURNAL SYSTÈME"

        onBackClicked: {
            if (root.StackView.view && root.StackView.view.depth > 1) {
                root.StackView.view.pop()
            }
        }
    }

    Timer {
        interval: 1000
        running: root.visible
        repeat: true
        onTriggered: {
            if (!bridge) {
                return
            }
            const raw = bridge.getRecentLogs(120)
            const events = raw ? JSON.parse(raw) : []
            let lines = []
            for (let i = 0; i < events.length; i++) {
                const ev = events[i]
                lines.push("[" + ev.ts + "] [" + ev.level + "] [" + ev.logger + "] " + ev.message)
            }
            root.logsText = lines.join("\n")
        }
    }

    ColumnLayout {
        anchors {
            top: header.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            margins: 20
        }
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Button {
                text: "Exporter diagnostic"
                onClicked: {
                    if (bridge) {
                        root.bundlePath = bridge.exportDiagnosticBundle()
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.bundlePath !== "" ? ("Bundle: " + root.bundlePath) : ""
                color: T.Theme.unselected
                elide: Text.ElideMiddle
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: T.Theme.bgDimmed
            radius: 10
            border.color: Qt.rgba(1, 1, 1, 0.08)

            ScrollView {
                anchors.fill: parent
                clip: true

                TextArea {
                    readOnly: true
                    text: root.logsText
                    wrapMode: Text.NoWrap
                    font.family: "Monospace"
                    color: T.Theme.textMain
                    background: null
                }
            }
        }
    }
}