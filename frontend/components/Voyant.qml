import QtQuick

Rectangle {
    id: root
    property bool isActive: false
    property string activeColor: "#00ff00"
    property string label: "Voyant"

    // Chemin vers l'icône optionnelle.
    property string iconSource: ""

    width: 60
    height: 60
    radius: width / 2 // Conserve une forme circulaire.

    color: isActive ? activeColor : "#222222"
    Behavior on color { ColorAnimation { duration: 150 } }

    // Affiche le libellé si aucune icône n'est définie.
    Text {
        visible: root.iconSource === ""
        anchors.centerIn: parent
        text: root.label
        color: isActive ? "#ffffff" : "#666666"
        font.bold: true
        font.pixelSize: 12
    }

    // Affiche l'icône si elle est définie.
    Image {
        visible: root.iconSource !== ""
        anchors.centerIn: parent
        source: root.iconSource
        width: parent.width * 0.6 // Taille relative de l'icône.
        height: parent.height * 0.6
        fillMode: Image.PreserveAspectFit
        opacity: isActive ? 1.0 : 0.3 // Opacité réduite à l'état inactif.
    }
}