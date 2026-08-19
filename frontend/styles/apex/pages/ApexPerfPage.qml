import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T
import "../components"

Item {
    id: root
    anchors.fill: parent

    signal actionRequested(string action)
    signal navigateRequested(string target)

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 14

        ApexCard3D {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1120
            title: "POWERTRAIN  /  TEMPS RÉEL"
            highlighted: S.UiState.redline
            glowColor: S.UiState.redline ? "#FF5964" : T.StyleManager.accent

            ColumnLayout {
                anchors.fill: parent
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 112
                    spacing: 0

                    Repeater {
                        model: [
                            { label: "PUISSANCE", value: S.UiState.fixed(S.UiState.powerHp, 0, "0"), unit: "ch", color: T.StyleManager.accent },
                            { label: "COUPLE", value: S.UiState.fixed(S.UiState.torque, 0, "0"), unit: "N·m", color: "#FFFFFF" },
                            { label: "RÉGIME", value: Math.round(S.UiState.rpm), unit: "tr/min", color: S.UiState.redline ? "#FF6670" : "#FFFFFF" }
                        ]
                        delegate: Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            Column {
                                anchors.centerIn: parent
                                spacing: -2
                                Text { text: modelData.label; color: "#AABACA"; font.pixelSize: 12; font.bold: true; font.letterSpacing: 1.8 }
                                Row {
                                    spacing: 7
                                    Text { text: modelData.value; color: modelData.color; font.pixelSize: 52; font.weight: Font.Black; font.letterSpacing: -2 }
                                    Text { anchors.baseline: parent.children[0].baseline; text: modelData.unit; color: "#AABACA"; font.pixelSize: 14; font.bold: true }
                                }
                            }
                            Rectangle { visible: index > 0; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; width: 1; height: 68; color: "#30465A" }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 236
                    radius: 18
                    color: "#080E15"
                    border.width: 1
                    border.color: "#253A4D"

                    Canvas {
                        id: dynoGraph
                        anchors.fill: parent
                        anchors.margins: 16
                        property real rpm: S.UiState.rpm
                        property real power: S.UiState.power
                        property real torque: S.UiState.torque
                        property var curve: S.UiState.engineCurve
                        property real maxPower: S.UiState.maxPowerHp
                        property real maxTorque: S.UiState.maxTorqueNm
                        onRpmChanged: requestPaint()
                        onPowerChanged: requestPaint()
                        onTorqueChanged: requestPaint()
                        onCurveChanged: requestPaint()
                        onMaxPowerChanged: requestPaint()
                        onMaxTorqueChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.reset()
                            var w = width, h = height
                            if (w < 100 || h < 80) return

                            ctx.lineWidth = 1
                            for (var x = 0; x <= 8; ++x) {
                                ctx.beginPath(); ctx.moveTo(x * w / 8, 0); ctx.lineTo(x * w / 8, h)
                                ctx.strokeStyle = "#162431"; ctx.stroke()
                            }
                            for (var y = 0; y <= 4; ++y) {
                                ctx.beginPath(); ctx.moveTo(0, y * h / 4); ctx.lineTo(w, y * h / 4)
                                ctx.strokeStyle = "#162431"; ctx.stroke()
                            }

                            var points = curve
                            if (!points || points.length < 2) return

                            function drawCurve(color, powerCurve, alpha) {
                                ctx.beginPath()
                                for (var i = 0; i < points.length; ++i) {
                                    var pointRpm = Number(points[i].rpm)
                                    var pointTorque = Number(points[i].torque_nm)
                                    var value = powerCurve
                                        ? (pointRpm * pointTorque / 9549.0 * 1.359621617) / Math.max(1, maxPower)
                                        : pointTorque / Math.max(1, maxTorque)
                                    var xx = Math.max(0, Math.min(1, pointRpm / Math.max(1, S.UiState.maxRpm))) * w
                                    var yy = h * (0.88 - Math.max(0, Math.min(1.05, value)) * 0.70)
                                    if (i === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy)
                                }
                                ctx.strokeStyle = color
                                ctx.globalAlpha = alpha
                                ctx.lineWidth = 3
                                ctx.stroke()
                                ctx.globalAlpha = 1
                            }
                            drawCurve(T.StyleManager.accent, true, 1.0)
                            drawCurve("#FFFFFF", false, 0.72)

                            var liveX = Math.max(0.03, Math.min(0.97, rpm / Math.max(1, S.UiState.maxRpm))) * w
                            ctx.beginPath(); ctx.moveTo(liveX, 0); ctx.lineTo(liveX, h)
                            ctx.strokeStyle = S.UiState.redline ? "#FF5964" : "#FFB84D"
                            ctx.lineWidth = 2; ctx.stroke()
                            ctx.fillStyle = S.UiState.redline ? "#FF5964" : "#FFB84D"
                            ctx.beginPath(); ctx.arc(liveX, h * 0.17, 6, 0, Math.PI * 2); ctx.fill()
                        }
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 18
                        spacing: 20
                        Row { spacing: 7; Rectangle { width: 16; height: 3; radius: 2; color: T.StyleManager.accent; anchors.verticalCenter: parent.verticalCenter } Text { text: "PUISSANCE  ·  " + Math.round(S.UiState.maxPowerHp) + " CH À " + Math.round(S.UiState.maxPowerRpm) + " TR/MIN"; color: "#C0CEDA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.0 } }
                        Row { spacing: 7; Rectangle { width: 16; height: 3; radius: 2; color: "#FFFFFF"; opacity: 0.72; anchors.verticalCenter: parent.verticalCenter } Text { text: "COUPLE  ·  " + Math.round(S.UiState.maxTorqueNm) + " N·M À " + Math.round(S.UiState.maxTorqueRpm) + " TR/MIN"; color: "#C0CEDA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.0 } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 92
                    spacing: 12

                    Repeater {
                        model: [
                            { label: "ACCÉLÉRATEUR", value: Math.min(1, S.UiState.throttle / 100), text: S.UiState.fixed(S.UiState.throttle, 0, "0") + " %", color: T.StyleManager.accent },
                            { label: "CHARGE LATÉRALE", value: Math.min(1, Math.abs(S.UiState.gForce)), text: S.UiState.fixed(S.UiState.gForce, 2, "0,00") + " G", color: "#FFB84D" }
                        ]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 15
                            color: "#0A131C"
                            border.width: 1
                            border.color: "#293F52"
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 6
                                RowLayout { Layout.fillWidth: true; Text { text: modelData.label; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2 } Item { Layout.fillWidth: true } Text { text: modelData.text; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true } }
                                Rectangle { Layout.fillWidth: true; height: 8; radius: 4; color: "#162431"; Rectangle { width: Math.max(7, parent.width * modelData.value); height: parent.height; radius: 4; color: modelData.color } }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.preferredWidth: 560
            Layout.minimumWidth: 520
            Layout.fillHeight: true
            spacing: 14

            ApexCard3D {
                Layout.fillWidth: true
                Layout.preferredHeight: 285
                title: "EFFICIENCE"

                RowLayout {
                    anchors.fill: parent
                    spacing: 20
                    Column {
                        Layout.fillWidth: true
                        spacing: -5
                        Text { text: S.UiState.fixed(S.UiState.instantCons, 1, "—"); color: S.UiState.instantCons > 14 ? "#FFB84D" : "#54E3A5"; font.pixelSize: 72; font.weight: Font.Black; font.letterSpacing: -3 }
                        Text { text: "L/100 KM INSTANTANÉ"; color: "#AABACA"; font.pixelSize: 12; font.bold: true; font.letterSpacing: 1.4 }
                    }
                    Column {
                        Layout.alignment: Qt.AlignRight
                        spacing: 6
                        Text { anchors.right: parent.right; text: S.UiState.fixed(S.UiState.avgConsB, 1, "—"); color: "#FFFFFF"; font.pixelSize: 32; font.bold: true }
                        Text { anchors.right: parent.right; text: "MOYENNE B"; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2 }
                    }
                }
            }

            ApexCard3D {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "SIGNATURE DU TRAJET"

                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    rowSpacing: 8
                    columnSpacing: 8

                    Repeater {
                        model: [
                            { label: "DISTANCE", value: S.UiState.fixed(S.UiState.tripDistance, 1, "0"), unit: "km" },
                            { label: "RÉGIME MOY.", value: Math.round(S.UiState.avgRpm), unit: "rpm" },
                            { label: "DÉCÉL. SANS GAZ", value: S.UiState.fixed(S.UiState.decelerationWithoutThrottleKm, 1, "0"), unit: "km" },
                            { label: "AGRESSIVITÉ", value: S.UiState.fixed(S.UiState.aggressivityPct, 0, "0"), unit: "%" }
                        ]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 16
                            color: "#0A121B"
                            border.width: 1
                            border.color: "#263B4E"
                            Column {
                                anchors.centerIn: parent
                                spacing: 4
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: "#AABACA"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2 }
                                Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: 5; Text { text: modelData.value; color: "#FFFFFF"; font.pixelSize: 28; font.bold: true } Text { anchors.baseline: parent.children[0].baseline; text: modelData.unit; color: "#9FB0C0"; font.pixelSize: 12; font.bold: true } }
                            }
                        }
                    }
                }
            }
        }
    }
}
