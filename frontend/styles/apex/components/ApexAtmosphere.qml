import QtQuick
import "../../../style" as T
import "../../../state" as S

// Fond cockpit épuré haute visibilité en plein jour — Zéro consommation CPU
Rectangle {
    id: root
    anchors.fill: parent
    color: "#03060B"

    // Subtil dégradé zénithal pour profondeur de cockpit
    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop { position: 0.0; color: "#070D18" }
        GradientStop { position: 0.5; color: "#03070E" }
        GradientStop { position: 1.0; color: "#010307" }
    }

    // Lignes de séparation de structure cockpit très nettes
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Qt.rgba(1, 1, 1, 0.05)
    }
}
