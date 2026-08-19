import QtQuick
import "../../../style" as T

Item {
    id: root
    anchors.fill: parent

    // Fond ultra-profond noir obsidienne haute lisibilité (Zéro particule, 100% contraste pour écran USB)
    Rectangle {
        anchors.fill: parent
        color: "#05080E"

        // Subtile nuance zénithale statique pour la profondeur sans surcharge CPU
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0B111A" }
                GradientStop { position: 0.5; color: "#06090F" }
                GradientStop { position: 1.0; color: "#030508" }
            }
        }
    }
}
