import QtQuick

Rectangle {
    id: root
    property bool isActive: false
    property string activeColor: "#00ff00"
    property string label: "Voyant"

    // NOUVEAUTÉ : Le chemin vers l'image (vide par défaut)
    property string iconSource: ""

    width: 60
    height: 60
    radius: width / 2 // S'adapte mathématiquement à la taille

    color: isActive ? activeColor : "#222222"
    Behavior on color { ColorAnimation { duration: 150 } }

    // CAS 1 : Pas d'image -> On affiche le texte
    Text {
        visible: root.iconSource === ""
        anchors.centerIn: parent
        text: root.label
        color: isActive ? "#ffffff" : "#666666"
        font.bold: true
        font.pixelSize: 12
    }

    // CAS 2 : Une image est fournie -> On affiche l'image
    Image {
        visible: root.iconSource !== ""
        anchors.centerIn: parent
        source: root.iconSource
        width: parent.width * 0.6 // L'icône prend 60% de la pastille
        height: parent.height * 0.6
        fillMode: Image.PreserveAspectFit
        opacity: isActive ? 1.0 : 0.3 // Légèrement transparent si éteint
    }
}