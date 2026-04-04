import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T
import "tabs"

Item {
    id: root
    width: 950
    height: 530

    readonly property var tabs: [
        { name: "Carplay",  accent: "#7B6FD0" },
        { name: "Race",     accent: "#C0726A" },
        { name: "Stats",    accent: "#6A9FB5" },
        { name: "Diag",     accent: "#6AB5A0" },
        { name: "Settings", accent: T.Theme.mainLight }
    ]
    property int  currentIndex: 4
    readonly property real borderW:     1.5
    readonly property int  tabRadius:   10
    readonly property int  panelRadius: 14

    // ─── PANEL PRINCIPAL ──────────────────────────────────────────────────────
    // Démarre sous les onglets. La bordure du haut a un "trou" grâce à
    // un Rectangle de la couleur du fond collé dessus (aucun Canvas).
    Rectangle {
        id: panel
        anchors {
            top:    tabRow.bottom
            bottom: parent.bottom
            left:   parent.left
            right:  parent.right
            // Remonte d'exactement 1 trait pour fusionner avec l'onglet actif
            topMargin: -borderW
        }
        color:        T.Theme.bgMain
        radius:       panelRadius
        border.color: root.tabs[root.currentIndex].accent
        border.width: borderW

        // Ce Rectangle "efface" la bordure haute sous l'onglet actif.
        // Il est positionné par rapport au panel via les x/width de tabRow.
        Rectangle {
            id: gapEraser
            y:      0
            x:      activeTabItem.x + tabRow.x - panel.x  // aligne sur l'onglet actif
            // +1/-2 pour mordre légèrement sous la bordure et la couvrir proprement
            width:  activeTabItem.width
            height: borderW + 1
            color:  T.Theme.bgMain
            // Pas de z spécial : il est dans le panel, dessiné sur sa bordure
        }

        // Contenu
        Item {
            anchors {
                fill:         parent
                margins:      borderW
                topMargin:    borderW + 6
            }
            clip: true

            CarplayTab  { visible: root.currentIndex === 0; anchors.fill: parent }
            RaceTab     { visible: root.currentIndex === 1; anchors.fill: parent }
            StatsTab    { visible: root.currentIndex === 2; anchors.fill: parent }
            DiagTab     { visible: root.currentIndex === 3; anchors.fill: parent }
            SettingsTab { visible: root.currentIndex === 4; anchors.fill: parent }
        }
    }

    // ─── BARRE D'ONGLETS ──────────────────────────────────────────────────────
    // Déclarée APRÈS le panel → z naturellement supérieur → clics non bloqués.
    // RowLayout pour que les onglets remplissent toute la largeur.
    RowLayout {
        id: tabRow
        anchors {
            top:   parent.top
            left:  parent.left
            right: parent.right
            // Indente pour que les onglets commencent après le rayon du panel
            leftMargin:  panelRadius
            rightMargin: panelRadius
        }
        height:  50
        spacing: 4

        Repeater {
            id: tabRepeater
            model: root.tabs

            delegate: Item {
                id: tabDelegate
                Layout.fillWidth:  true
                Layout.fillHeight: true

                // Référence à l'item actif pour le gapEraser
                readonly property bool isActive: index === root.currentIndex

                // Fond + bordure du tab via deux Rectangle superposés
                // (coins arrondis en haut uniquement via clip + rectangle décalé)
                Rectangle {
                    id: tabBg
                    anchors.fill: parent
                    color:        T.Theme.bgMain

                    // Coins arrondis uniquement en haut :
                    // on utilise un Rectangle avec radius complet + un autre
                    // Rectangle carré collé en bas pour "cacher" les coins bas
                    radius: tabRadius

                    Rectangle {
                        // Couvre les coins bas arrondis → donne l'impression
                        // que seuls les coins hauts sont arrondis
                        anchors {
                            left:   parent.left
                            right:  parent.right
                            bottom: parent.bottom
                        }
                        height: tabRadius
                        color:  T.Theme.bgMain
                    }

                    // Bordure colorée (même technique : Rectangle border + cache bas)
                    Rectangle {
                        anchors.fill: parent
                        color:        "transparent"
                        radius:       tabRadius
                        border.color: tabDelegate.isActive
                                      ? root.tabs[root.currentIndex].accent
                                      : modelData.accent
                        border.width: borderW

                        // Cache le bas de la bordure pour l'onglet actif
                        Rectangle {
                            visible: tabDelegate.isActive
                            anchors {
                                left:         parent.left
                                right:        parent.right
                                bottom:       parent.bottom
                                leftMargin:   borderW
                                rightMargin:  borderW
                            }
                            height: tabRadius
                            color:  T.Theme.bgMain
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text:  modelData.name
                    color: tabDelegate.isActive ? T.Theme.textMain : Qt.rgba(1, 1, 1, 0.4)
                    font.pixelSize: 16
                    font.weight:    tabDelegate.isActive ? Font.Medium : Font.Normal
                }

                MouseArea {
                    anchors.fill:            parent
                    cursorShape:             Qt.PointingHandCursor
                    propagateComposedEvents: false
                    onClicked: (mouse) => {
                        root.currentIndex = index
                        mouse.accepted = true
                    }
                }
            }
        }
    }

    // Référence à l'item actif pour le gapEraser (cherche dans les delegates)
    property Item activeTabItem: {
        for (var i = 0; i < tabRepeater.count; i++) {
            var item = tabRepeater.itemAt(i)
            if (item && item.isActive) return item
        }
        return tabRow   // fallback
    }
}