import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    objectName: "servicesSettingsPage"
    property bool embedded: false
    signal backRequested()
    readonly property var serviceKeys: Object.keys(S.UiState.serviceHealth)
    function serviceItem(serviceId) {
        const items = servicesList.contentItem.children
        for (let index = 0; index < items.length; ++index) {
            const item = items[index]
            if (item && item.serviceId === serviceId)
                return item
        }
        return null
    }
    function toggleServiceDetails(serviceId) {
        const item = serviceItem(serviceId)
        if (!item || !item.hasParams)
            return false
        item.toggleDetails()
        return true
    }
    function serviceExpanded(serviceId) {
        const item = serviceItem(serviceId)
        return item ? item.expanded : false
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.embedded ? 0 : 16
        spacing: root.embedded ? 0 : 12

        PageHeader {
            visible: !root.embedded
            Layout.fillWidth: true
            title: "Services"
            subtitle: root.serviceKeys.length + " module(s) supervisé(s)"
            onBackClicked: root.backRequested()
        }

        ListView {
            id: servicesList
            objectName: "servicesList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 10
            model: root.serviceKeys
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: serviceRow
                objectName: "expandableServiceRow"
                width: ListView.view.width
                height: header.height + (expanded ? parametersColumn.implicitHeight + 20 : 0)
                radius: T.StyleManager.radiusSmall
                color: T.StyleManager.surface
                border.width: 1
                border.color: expanded ? T.StyleManager.accent : T.StyleManager.outline
                clip: true

                property string serviceId: String(modelData)
                property var details: S.UiState.serviceHealth[serviceId] || ({})
                property bool running: details.status !== "DISABLED"
                property bool expanded: false
                property var params: []
                readonly property bool hasParams: params.length > 0

                function reloadParams() {
                    try {
                        const raw = bridge.getServiceParameters(serviceId)
                        params = raw ? JSON.parse(raw) : []
                    } catch (error) {
                        console.warn("Paramètres du service " + serviceId + " illisibles: " + error)
                        params = []
                    }
                }

                function setParameter(key, value, refreshAfter) {
                    bridge.setServiceParameter(serviceId, key, value)
                    if (refreshAfter)
                        reloadParams()
                }

                function toggleDetails() {
                    if (!hasParams)
                        return
                    if (!expanded)
                        reloadParams()
                    expanded = !expanded
                }

                Behavior on height {
                    NumberAnimation {
                        duration: T.StyleManager.durationNormal
                        easing.type: Easing.OutCubic
                    }
                }
                Behavior on border.color { ColorAnimation { duration: T.StyleManager.durationFast } }

                Component.onCompleted: reloadParams()

                Item {
                    id: header
                    width: parent.width
                    height: 82

                    Rectangle {
                        anchors.fill: parent
                        color: headerTouch.pressed ? T.StyleManager.surfaceRaised : "transparent"
                    }

                    MouseArea {
                        id: headerTouch
                        anchors.fill: parent
                        enabled: serviceRow.hasParams
                        onClicked: serviceRow.toggleDetails()
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 18
                        anchors.rightMargin: 18
                        spacing: 14

                        Rectangle {
                            width: 12
                            height: 12
                            radius: 6
                            color: serviceRow.details.status === "ERROR" ? T.StyleManager.danger
                                  : serviceRow.details.status === "WARNING" ? T.StyleManager.warning
                                  : serviceRow.running ? T.StyleManager.success
                                  : T.StyleManager.textSecondary
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                Layout.fillWidth: true
                                text: serviceRow.serviceId
                                color: T.StyleManager.text
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: serviceRow.details.message || serviceRow.details.status || "État inconnu"
                                color: T.StyleManager.textSecondary
                                font.family: T.StyleManager.fontFamily
                                font.pixelSize: 14
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            visible: serviceRow.hasParams
                            text: serviceRow.params.length + " paramètre" + (serviceRow.params.length > 1 ? "s" : "")
                            color: T.StyleManager.textSecondary
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 14
                        }

                        Text {
                            visible: serviceRow.hasParams
                            text: "›"
                            color: T.StyleManager.accent
                            font.family: T.StyleManager.fontFamily
                            font.pixelSize: 34
                            rotation: serviceRow.expanded ? 90 : 0
                            Behavior on rotation { NumberAnimation { duration: T.StyleManager.durationNormal } }
                        }

                        Toggle {
                            Layout.leftMargin: 6
                            checked: serviceRow.running
                            onToggled: checked => bridge.toggleService(serviceRow.serviceId, checked)
                        }
                    }
                }

                Column {
                    id: parametersColumn
                    objectName: "serviceParameters"
                    visible: serviceRow.expanded
                    x: 16
                    y: header.height + 2
                    width: parent.width - 32
                    spacing: 8

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: T.StyleManager.outline
                    }

                    Repeater {
                        model: serviceRow.params

                        delegate: Rectangle {
                            id: parameterRow
                            width: parametersColumn.width
                            height: 58
                            radius: T.StyleManager.radiusSmall
                            color: T.StyleManager.surfaceSoft

                            readonly property string parameterType: String(modelData.type || "")

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16
                                spacing: 16

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.label || modelData.key
                                    color: T.StyleManager.text
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 15
                                    elide: Text.ElideRight
                                }

                                Text {
                                    visible: parameterRow.parameterType === "slider"
                                    text: Number(modelData.value).toLocaleString(
                                              Qt.locale(), "f", Number(modelData.value) % 1 === 0 ? 0 : 2)
                                    color: T.StyleManager.accent
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    Layout.preferredWidth: 70
                                    horizontalAlignment: Text.AlignRight
                                }

                                Toggle {
                                    visible: parameterRow.parameterType === "toggle"
                                    checked: Boolean(modelData.value)
                                    onToggled: checked => serviceRow.setParameter(modelData.key, checked, true)
                                }

                                Slider {
                                    visible: parameterRow.parameterType === "slider"
                                    Layout.preferredWidth: 310
                                    from: modelData.min_val !== undefined ? Number(modelData.min_val) : 0
                                    to: modelData.max_val !== undefined ? Number(modelData.max_val) : 100
                                    value: Number(modelData.value || 0)
                                    onMoved: serviceRow.setParameter(modelData.key, value, false)
                                }

                                ComboBox {
                                    visible: parameterRow.parameterType === "list"
                                    Layout.preferredWidth: 310
                                    model: modelData.options || []
                                    currentIndex: Math.max(0, (modelData.options || []).indexOf(modelData.value))
                                    onActivated: serviceRow.setParameter(modelData.key, currentText, true)
                                }

                                TextField {
                                    visible: parameterRow.parameterType === "text"
                                             || parameterRow.parameterType === "number"
                                    Layout.preferredWidth: 310
                                    text: String(modelData.value === undefined ? "" : modelData.value)
                                    color: T.StyleManager.text
                                    font.family: T.StyleManager.fontFamily
                                    font.pixelSize: 15
                                    selectByMouse: true
                                    inputMethodHints: parameterRow.parameterType === "number"
                                                      ? Qt.ImhFormattedNumbersOnly : Qt.ImhNone
                                    background: Rectangle {
                                        radius: T.StyleManager.radiusSmall
                                        color: T.StyleManager.surfaceRaised
                                        border.width: 1
                                        border.color: parent.activeFocus
                                                      ? T.StyleManager.accent : T.StyleManager.outline
                                    }
                                    onEditingFinished: {
                                        const nextValue = parameterRow.parameterType === "number"
                                                        ? Number(text) : text
                                        serviceRow.setParameter(modelData.key, nextValue, true)
                                    }
                                }

                                Button {
                                    visible: parameterRow.parameterType === "button"
                                    Layout.preferredWidth: 210
                                    Layout.preferredHeight: 56
                                    text: "EXÉCUTER"
                                    onClicked: serviceRow.setParameter(modelData.key, true, true)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
