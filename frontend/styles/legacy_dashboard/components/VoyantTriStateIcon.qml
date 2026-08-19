import QtQuick
import QtQuick.Effects

Item {
    id: root
    width: 60
    height: 60

    // 1. Les signaux CAN à écouter
    property bool isPos1: false
    property bool isPos2: false

    // 2. Les chemins vers tes fichiers SVG
    property url iconPos1: ""
    property url iconPos2: ""
    property url iconOff: ""

    // 3. Les couleurs
    property color colorPos1: "#00ff00" // Vert
    property color colorPos2: "#0000ff" // Bleu
    property color colorOff: "#222222"  // Gris foncé

    // LA MAGIE : Calcul des états
    property url currentIcon: isPos2 ? iconPos2 : (isPos1 ? iconPos1 : iconOff)
    property color currentColor: isPos2 ? colorPos2 : (isPos1 ? colorPos1 : colorOff)

    // L'animation de transition de couleur
    Behavior on currentColor { ColorAnimation { duration: 5 } }

    // ÉTAPE A : On charge le SVG original en tant que "Patron" invisible
    Image {
        id: baseImage
        anchors.fill: parent
        anchors.margins: 5
        source: root.currentIcon

        // sourceSize garantit que le SVG reste net même si tu agrandis le composant
        sourceSize: Qt.size(width, height)
        fillMode: Image.PreserveAspectFit

        visible: false
    }

    // ÉTAPE B : Le filtre de couleur qui agit comme un pochoir
    MultiEffect {
        anchors.fill: baseImage
        source: baseImage

        // On active le mode "Colorisation pure"
        colorization: 1.0
        colorizationColor: root.currentColor

        // Le composant s'efface s'il n'y a pas de lien SVG
        visible: baseImage.source.toString() !== ""
    }
}