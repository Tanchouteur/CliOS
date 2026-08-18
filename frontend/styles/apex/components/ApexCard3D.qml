import QtQuick
import "../../../style" as T

// Carte avec effet 3D : Biseau cristal + Reflet supérieur + Double ombre d'élévation (GPU pur)
Item {
    id: root
    property string title:       ""
    property bool   highlighted: false
    property color  glowColor:   T.StyleManager.accent
    property alias  content:     contentItem.data
    default property alias contentData: contentItem.data

    // Animation d'apparition fluide 3D
    property real entryProgress: 0.0
    NumberAnimation on entryProgress {
        from: 0.0; to: 1.0; duration: 380; easing.type: Easing.OutCubic
        running: true
    }

    opacity: entryProgress
    transform: Translate { y: (1.0 - root.entryProgress) * 12 }

    // ── 1. Double ombre portée 3D (Effet de lévitation au-dessus du fond) ─────
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 6
        anchors.leftMargin: 3
        anchors.rightMargin: 3
        radius: T.StyleManager.radiusMedium
        color: Qt.rgba(0, 0, 0, 0.60)
        z: -2
    }
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 3
        anchors.leftMargin: 1
        anchors.rightMargin: 1
        radius: T.StyleManager.radiusMedium
        color: Qt.rgba(0, 0, 0, 0.35)
        z: -1
    }

    // ── 2. Corps de la carte en verre fumé et titane ─────────────────────────
    Rectangle {
        id: cardBody
        anchors.fill: parent
        radius: T.StyleManager.radiusMedium
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#0F1826" }
            GradientStop { position: 0.5; color: "#0A101A" }
            GradientStop { position: 1.0; color: "#060A12" }
        }

        border.width: 1
        border.color: root.highlighted
            ? Qt.rgba(root.glowColor.r, root.glowColor.g, root.glowColor.b, 0.55)
            : Qt.rgba(root.glowColor.r, root.glowColor.g, root.glowColor.b, 0.14)

        Behavior on border.color { ColorAnimation { duration: 250 } }

        // ── 3. Biseau supérieur biseauté (Lumière zénithale 3D) ───────────────
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            radius: parent.radius
            color: Qt.rgba(1.0, 1.0, 1.0, 0.14)
        }

        // Ligne d'accent supérieure dynamique (si highlighted)
        Rectangle {
            visible: root.highlighted
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2
            radius: parent.radius
            color: root.glowColor
        }
    }

    // ── 4. Titre gravé haute lisibilité ──────────────────────────────────────
    Text {
        id: titleText
        visible: root.title !== ""
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.topMargin: 12
        anchors.leftMargin: 16
        text: root.title.toUpperCase()
        color: Qt.rgba(1.0, 1.0, 1.0, 0.45)
        font.pixelSize: 11
        font.weight: Font.Bold
        font.letterSpacing: 2.0
    }

    // ── 5. Conteneur des éléments internes ───────────────────────────────────
    Item {
        id: contentItem
        anchors {
            left:   parent.left
            right:  parent.right
            bottom: parent.bottom
            top:    root.title !== "" ? titleText.bottom : parent.top
        }
        anchors.margins:   12
        anchors.topMargin: root.title !== "" ? 8 : 12
    }
}
