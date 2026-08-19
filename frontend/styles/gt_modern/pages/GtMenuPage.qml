import QtQuick
import QtQuick.Layouts
import "../components"
import "../../../style" as T

Item {
    id: root
    signal navigateRequested(string destination)
    signal actionRequested(string action)
    readonly property var sections: [
        { id: "appearance", title: "APPARENCE", desc: "Styles installés et accent lumineux" },
        { id: "vehicle", title: "VÉHICULE", desc: "Profils, configuration et étalonnage" },
        { id: "services", title: "SERVICES", desc: "État et paramètres des modules" },
        { id: "system", title: "SYSTÈME", desc: "Ressources, stockage, logs et export" },
        { id: "developer", title: "DÉVELOPPEUR", desc: "Inspection complète des données CAN" }
    ]

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 14
        Text { text: "MENU CLIOS GT"; color: T.StyleManager.text; font.pixelSize: 28; font.weight: Font.DemiBold }
        GridLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; columns: 3; rowSpacing: 14; columnSpacing: 14
            Repeater {
                model: root.sections
                GtButton {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    text: modelData.title; subtext: modelData.desc
                    primary: modelData.id === "appearance"
                    onClicked: root.navigateRequested(modelData.id)
                }
            }
            GtCard {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "Alimentation"
                ColumnLayout {
                    anchors.fill: parent; spacing: 12
                    GtButton { Layout.fillWidth: true; Layout.fillHeight: true; text: "QUITTER CLIOS"; onClicked: root.actionRequested("quit") }
                    GtButton { Layout.fillWidth: true; Layout.fillHeight: true; text: "REDÉMARRER"; destructive: true; onClicked: root.actionRequested("restart") }
                    GtButton { Layout.fillWidth: true; Layout.fillHeight: true; text: "ÉTEINDRE"; destructive: true; onClicked: root.actionRequested("shutdown") }
                }
            }
        }
    }
}
