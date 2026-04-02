import QtQuick

Rectangle {
    id: root
    width: 60
    height: 60
    radius: width / 2 // Toujours rond

    // 1. Les deux signaux CAN à écouter
    property bool isPos1: false // Ex: Croisement
    property bool isPos2: false // Ex: Plein phare

    // 2. Les couleurs configurables
    property string colorPos1: "#00ff00" // Vert
    property string colorPos2: "#0000ff" // Bleu
    property string colorOff: "#222222"  // Gris foncé

    // 3. Le texte dynamique (Bonus !)
    property string label: "FEUX"

    // LA MAGIE TRI-STATE :
    // Si Pos2 est Vrai -> Couleur2. SINON, si Pos1 est Vrai -> Couleur1. SINON -> Off.
    color: isPos2 ? colorPos2 : (isPos1 ? colorPos1 : colorOff)

    Behavior on color { ColorAnimation { duration: 150 } }

    Text {
        anchors.centerIn: parent
        text: root.label
        // Si l'un des deux est allumé, texte blanc, sinon texte grisé
        color: (isPos1 || isPos2) ? "#ffffff" : "#666666"
        font.bold: true
        font.pixelSize: 12
    }
}