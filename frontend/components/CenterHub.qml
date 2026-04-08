import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T
import "tabs"

Item {
    id: root
    width: 950
    height: 530

    readonly property var tabs: [
        { name: "Race"      },
        { name: "Stats"     },
        { name: "Diag"      },
        { name: "Settings"  },
        { name: "Debug"     }
    ]
    property int  currentIndex: 1
    readonly property real borderW:     1.5
    readonly property int  tabRadius:   10
    readonly property int  panelRadius: 14

    // Panneau de Contenu
    Rectangle {
        z:20
        id: panel
        anchors {
            top:    tabRow.bottom
            bottom: parent.bottom
            left:   parent.left
            right:  parent.right
            topMargin: -borderW
        }
        color:        T.Theme.bgMain
        radius:       panelRadius

        border.color: T.Theme.main
        border.width: borderW

        Rectangle {
            id: gapEraser
            y:      0
            x:      activeTabItem.x + tabRow.x - panel.x
            width:  activeTabItem.width
            height: borderW + 1
            color:  T.Theme.bgMain
        }

        Item {
            anchors {
                fill:         parent
                margins:      borderW
                topMargin:    borderW + 6
            }
            clip: true


            RaceTab     { visible: root.currentIndex === 0; anchors.fill: parent; enabled: visible}
            StatsTab    { visible: root.currentIndex === 1; anchors.fill: parent; enabled: visible }
            DiagTab     { visible: root.currentIndex === 2; anchors.fill: parent; enabled: visible }
            SettingsTab { visible: root.currentIndex === 3; anchors.fill: parent; enabled: visible }
            DebugTab    { visible: root.currentIndex === 4; anchors.fill: parent; enabled: visible }
        }
    }

    // Barre d'onglets
    RowLayout {
        z: 2
        id: tabRow
        anchors {
            top:   parent.top
            left:  parent.left
            right: parent.right
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

                readonly property bool isActive: index === root.currentIndex

                Rectangle {
                    id: tabBg
                    anchors.fill: parent
                    color:        T.Theme.bgMain
                    radius:       tabRadius

                    Rectangle {
                        anchors {
                            left:   parent.left
                            right:  parent.right
                            bottom: parent.bottom
                        }
                        height: tabRadius
                        color:  T.Theme.bgMain
                    }

                    Rectangle {
                        anchors.fill: parent
                        color:        "transparent"
                        radius:       tabRadius

                        border.color: tabDelegate.isActive ? T.Theme.main : T.Theme.unselected
                        border.width: borderW

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
                    color: tabDelegate.isActive ? T.Theme.textMain : T.Theme.unselected
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

    property Item activeTabItem: {
        for (var i = 0; i < tabRepeater.count; i++) {
            var item = tabRepeater.itemAt(i)
            if (item && item.isActive) return item
        }
        return tabRow
    }
}