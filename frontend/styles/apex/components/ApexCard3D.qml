import QtQuick
import "../../../style" as T

// Carte avec effet 3D : Biseau cristal + Reflet supérieur + Glow respirant + Double ombre d'élévation
Item {
    id: root
    property string title:       ""
    property bool   highlighted: false
    property color  glowColor:   T.StyleManager.accent
    property alias  content:     contentItem.data
    default property alias contentData: contentItem.data

    // Phase du glow pulsatoire
    property real glowPhase: 0.0
    property real glowOpacity: 0.0

    SequentialAnimation on glowPhase {
        loops: Animation.Infinite
        NumberAnimation { from: 0; to: Math.PI * 2; duration: 3400; easing.type: Easing.Linear }
    }

    // Animation d'apparition fluide 3D
    property real entryProgress: 0.0
    NumberAnimation on entryProgress {
        from: 0; to: 1; duration: 420; easing.type: Easing.OutCubic
        running: true
    }

    opacity: entryProgress
    transform: Translate { y: (1.0 - root.entryProgress) * 14 }

    onGlowPhaseChanged: {
        glowOpacity = (highlighted ? 0.26 : 0.08) + Math.sin(glowPhase) * (highlighted ? 0.12 : 0.04)
    }

    // ── 1. Double ombre portée 3D (Effet de lévitation au-dessus du fond) ─────
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        radius: T.StyleManager.radiusMedium
        color: Qt.rgba(0, 0, 0, 0.65)
        z: -2
    }
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 4
        anchors.leftMargin: 2
        anchors.rightMargin: 2
        radius: T.StyleManager.radiusMedium
        color: Qt.rgba(0, 0, 0, 0.40)
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
        border.color: Qt.rgba(
            root.glowColor.r,
            root.glowColor.g,
            root.glowColor.b,
            root.glowOpacity
        )

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
        color: Qt.rgba(1, 1, 1, 0.45)
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
