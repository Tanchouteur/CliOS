import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../style" as T
import "../state" as S

Item {
    id: root
    signal backRequested()
    readonly property var serviceKeys: Object.keys(S.UiState.health)

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 12
        GtPageHeader { Layout.fillWidth: true; title: "Services"; subtitle: root.serviceKeys.length + " module(s) supervisé(s)"; onBackClicked: root.backRequested() }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 10; model: root.serviceKeys
            delegate: Rectangle {
                id: serviceRow
                width: ListView.view.width; height: expanded ? 170 : 82
                radius: T.StyleManager.radiusSmall; color: T.StyleManager.surface
                border.width: 1; border.color: T.StyleManager.outline; clip: true
                property string serviceId: String(modelData)
                property var details: S.UiState.health[serviceId] || ({})
                property bool running: details.status !== "DISABLED"
                property bool expanded: false
                property var params: []
                Behavior on height { NumberAnimation { duration: T.StyleManager.durationNormal } }
                Component.onCompleted: { const raw = bridge.getServiceParameters(serviceId); params = raw ? JSON.parse(raw) : [] }

                RowLayout {
                    x: 18; y: 10; width: parent.width - 36; height: 62; spacing: 16
                    Rectangle { width: 12; height: 12; radius: 6; color: details.status === "ERROR" ? T.StyleManager.danger : details.status === "WARNING" ? T.StyleManager.warning : running ? T.StyleManager.success : T.StyleManager.textSecondary }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: serviceRow.serviceId; color: T.StyleManager.text; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: details.message || details.status || "État inconnu"; color: T.StyleManager.textSecondary; font.pixelSize: 14; elide: Text.ElideRight }
                    }
                    GtButton { visible: serviceRow.params.length > 0; width: 150; height: 56; text: serviceRow.expanded ? "FERMER" : "RÉGLAGES"; onClicked: serviceRow.expanded = !serviceRow.expanded }
                    GtToggle { checked: serviceRow.running; onToggled: checked => bridge.toggleService(serviceRow.serviceId, checked) }
                }
                RowLayout {
                    visible: serviceRow.expanded; x: 24; y: 88; width: parent.width - 48; height: 65; spacing: 20
                    Repeater {
                        model: serviceRow.params
                        RowLayout {
                            Layout.fillWidth: true; spacing: 10
                            Text { text: modelData.label; color: T.StyleManager.textSecondary; font.pixelSize: 15; Layout.fillWidth: true; elide: Text.ElideRight }
                            GtToggle { visible: modelData.type === "toggle"; checked: modelData.value; onToggled: checked => bridge.setServiceParameter(serviceRow.serviceId, modelData.key, checked) }
                            Slider { visible: modelData.type === "slider"; Layout.preferredWidth: 180; from: modelData.min_val || 0; to: modelData.max_val || 100; value: modelData.value || 0; onMoved: bridge.setServiceParameter(serviceRow.serviceId, modelData.key, value) }
                            ComboBox { visible: modelData.type === "list"; Layout.preferredWidth: 180; model: modelData.options || []; onActivated: bridge.setServiceParameter(serviceRow.serviceId, modelData.key, currentText) }
                        }
                    }
                }
            }
        }
    }
}
