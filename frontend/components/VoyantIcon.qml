import QtQuick
import QtQuick.Effects

Item {
    id: root

    // Propriétés
    property bool isActive: false
    property color activeColor: "#00ff00"
    property color inactiveColor: "#333333"
    property string label: "Voyant"
    property url iconSource: ""

    width: 40 // Un peu plus petit par défaut vu qu'il n'y a plus de marges de fond
    height: 40

    // LA MAGIE : La variable de couleur centralisée
    // Si actif = couleur d'alerte. Si inactif = gris très sombre (légèrement visible)
    property color currentColor: isActive ? activeColor : inactiveColor

    // Animation fluide pour l'allumage/extinction
    Behavior on currentColor { ColorAnimation { duration: 150 } }

    // CAS 1 : Pas d'image -> Le texte fait office de néon
    Text {
        visible: root.iconSource.toString() === ""
        anchors.centerIn: parent
        text: root.label
        color: root.currentColor // Le texte prend la couleur calculée
        font.bold: true
        font.pixelSize: 18 // Un peu plus gros pour compenser l'absence de fond
    }

    // CAS 2 : Une image est fournie -> L'icône fait office de néon
    Item {
        visible: root.iconSource.toString() !== ""
        anchors.fill: parent

        Image {
            id: iconImg
            anchors.fill: parent
            source: root.iconSource
            sourceSize: Qt.size(width, height)
            fillMode: Image.PreserveAspectFit
            visible: false // Toujours caché pour le pochoir
        }

        MultiEffect {
            anchors.fill: iconImg
            source: iconImg
            colorization: 1.0
            // C'est ici que la couleur du SVG change dynamiquement !
            colorizationColor: root.currentColor
        }
    }
}