import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Rectangle {
    id: statusBar
    /* Augmentation de la hauteur pour une meilleure visibilite */
    height: 40
    width: parent.width * 0.25
    color: T.Theme.bgMain
    z: 100

    /* Recuperation des donnees de sante du systeme */
    property var health: bridge && bridge.systemHealth !== undefined ? bridge.systemHealth : {}
    property var allKeys: Object.keys(statusBar.health)

    /* Classification stricte des services par statut */
    property var errorKeys: allKeys.filter(function (k) {
        return statusBar.health[k].status === "ERROR";
    })
    property var warnKeys: allKeys.filter(function (k) {
        return statusBar.health[k].status === "WARNING";
    })
    property var disabledKeys: allKeys.filter(function (k) {
        return statusBar.health[k].status === "DISABLED";
    })
    property var okKeys: allKeys.filter(function (k) {
        return statusBar.health[k].status === "OK";
    })

    /* Variable de controle pour l'affichage des menus ("error", "warn", "disabled", "ok", "") */
    property string activeMenu: ""

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 12

        Item {
            Layout.fillWidth: true
        }

        Row {
            spacing: 10
            Layout.alignment: Qt.AlignVCenter

            /* Groupe 1 : Services en Erreur (Rouge) */
            Rectangle {
                width: errorKeys.length > 0 ? errorText.width + 30 : 0
                height: 28
                radius: 14
                color: Qt.rgba(1.0, 0.0, 0.0, 0.1)
                border.color: "#ff0000"
                border.width: 1
                visible: errorKeys.length > 0

                SequentialAnimation on opacity {
                    running: errorKeys.length > 0
                    loops: Animation.Infinite
                    NumberAnimation {
                        to: 0.5; duration: 800
                    }
                    NumberAnimation {
                        to: 1.0; duration: 800
                    }
                }

                Text {
                    id: errorText
                    text: errorKeys.length + " ERR"
                    color: "#ff0000"
                    font.pixelSize: 13
                    font.bold: true
                    anchors.centerIn: parent
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: statusBar.activeMenu = (statusBar.activeMenu === "error") ? "" : "error"
                }
            }

            /* Groupe 2 : Services en Avertissement (Orange) */
            Rectangle {
                width: warnKeys.length > 0 ? warnText.width + 30 : 0
                height: 28
                radius: 14
                color: Qt.rgba(1.0, 0.66, 0.0, 0.1)
                border.color: "#ffaa00"
                border.width: 1
                visible: warnKeys.length > 0

                Text {
                    id: warnText
                    text: warnKeys.length + " WARN"
                    color: "#ffaa00"
                    font.pixelSize: 13
                    font.bold: true
                    anchors.centerIn: parent
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: statusBar.activeMenu = (statusBar.activeMenu === "warn") ? "" : "warn"
                }
            }

            /* Groupe 3 : Services Eteints / Desactives (Bleu) */
            Rectangle {
                width: disabledKeys.length > 0 ? disabledText.width + 30 : 0
                height: 28
                radius: 14
                color: Qt.rgba(0.0, 0.5, 1.0, 0.1)
                border.color: "#0088ff"
                border.width: 1
                visible: disabledKeys.length > 0

                Text {
                    id: disabledText
                    text: disabledKeys.length + " OFF"
                    color: "#0088ff"
                    font.pixelSize: 13
                    font.bold: true
                    anchors.centerIn: parent
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: statusBar.activeMenu = (statusBar.activeMenu === "disabled") ? "" : "disabled"
                }
            }

            /* Groupe 4 : Services Operationnels (Vert) */
            Rectangle {
                width: okKeys.length > 0 ? okText.width + 25 : 0
                height: 28
                radius: 14
                color: Qt.rgba(0.0, 1.0, 0.0, 0.1)
                border.color: "#00ff00"
                border.width: 1
                visible: okKeys.length > 0

                Text {
                    id: okText
                    text: okKeys.length + " OK"
                    color: "#00ff00"
                    font.pixelSize: 13
                    font.bold: true
                    anchors.centerIn: parent
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: statusBar.activeMenu = (statusBar.activeMenu === "ok") ? "" : "ok"
                }
            }
        }
    }

    /* Template pour les menus deroulants */
    /* Menu ERROR */
    Rectangle {
        visible: statusBar.activeMenu === "error"
        anchors.top: statusBar.bottom; anchors.topMargin: 5; anchors.right: parent.right; anchors.rightMargin: 20
        width: 180; height: errorCol.height + 20; radius: 8; color: Qt.rgba(0.1, 0.1, 0.1, 0.95); border.color: Qt.rgba(1, 1, 1, 0.2)
        Column {
            id:
                errorCol; anchors.margins: 10; anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; spacing: 8
            Repeater {
                model: statusBar.errorKeys;
                delegate: Row {
                    spacing: 8;
                    Rectangle {
                        width: 8; height: 8; radius: 4; color: "#ff0000"; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: modelData; color: "white"; font.pixelSize: 12
                    }
                }
            }
        }
    }

    /* Menu WARN */
    Rectangle {
        visible: statusBar.activeMenu === "warn"
        anchors.top: statusBar.bottom; anchors.topMargin: 5; anchors.right: parent.right; anchors.rightMargin: 20
        width: 180; height: warnCol.height + 20; radius: 8; color: Qt.rgba(0.1, 0.1, 0.1, 0.95); border.color: Qt.rgba(1, 1, 1, 0.2)
        Column {
            id:
                warnCol; anchors.margins: 10; anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; spacing: 8
            Repeater {
                model: statusBar.warnKeys;
                delegate:
                    Row {
                        spacing: 8;
                        Rectangle {
                            width: 8; height: 8; radius: 4; color: "#ffaa00"; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData; color: "white"; font.pixelSize: 12
                        }
                    }
            }
        }
    }

    /* Menu DISABLED */
    Rectangle {
        visible: statusBar.activeMenu === "disabled"
        anchors.top: statusBar.bottom; anchors.topMargin: 5; anchors.right: parent.right; anchors.rightMargin: 20
        width: 180; height: disCol.height + 20; radius: 8; color: Qt.rgba(0.1, 0.1, 0.1, 0.95); border.color: Qt.rgba(1, 1, 1, 0.2)
        Column {
            id:
                disCol; anchors.margins: 10; anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; spacing: 8
            Repeater {
                model: statusBar.disabledKeys;
                delegate: Row {
                    spacing: 8; Rectangle {
                        width: 8; height: 8; radius: 4; color: "#0088ff"; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: modelData; color: "white"; font.pixelSize: 12
                    }
                }
            }
        }
    }

    /* Menu OK */
    Rectangle {
        visible: statusBar.activeMenu === "ok"
        anchors.top: statusBar.bottom; anchors.topMargin: 5; anchors.right: parent.right; anchors.rightMargin: 20
        width: 180; height: okCol.height + 20; radius: 8; color: Qt.rgba(0.1, 0.1, 0.1, 0.95); border.color: Qt.rgba(1, 1, 1, 0.2)
        Column {
            id:
                okCol; anchors.margins: 10; anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; spacing: 8
            Repeater {
                model: statusBar.okKeys;
                delegate: Row {
                    spacing: 8;
                    Rectangle {
                        width: 8; height: 8; radius: 4; color: "#00ff00"; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: modelData; color: "white"; font.pixelSize: 12
                    }
                }
            }
        }
    }
}