import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Item {
    id: profilePage

    // --- PROPRIÉTÉS ---
    property var profileList: []
    property string activeProfile: bridge.getActiveProfile()
    property string pendingProfile: bridge.getActiveProfile() // Stocke le choix avant redémarrage

    // Gestion d'état pour basculer entre la liste et le formulaire de création
    property bool isCreatingForm: false
    // Gestion d'état pour le type de configuration (existant vs nouveau)
    property bool createNewConfig: false

    // Initialisation au chargement de la page
    Component.onCompleted: {
        refreshData()
    }

    // Rafraîchissement manuel
    function refreshData() {
        profileList = bridge.getAvailableProfiles()
        canCombo.model = bridge.getAvailableCanFiles()
        confCombo.model = bridge.getAvailableConfigFiles()
    }

    // --- HEADER DYNAMIQUE (Inspiré de SystemPage) ---
    RowLayout {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 20; leftMargin: 30; rightMargin: 30 }
        spacing: 15

        Rectangle {
            width: 40; height: 40; radius: 20
            color: backMouse.pressed ? T.Theme.main : (backMouse.containsMouse ? T.Theme.main : T.Theme.bgDimmed)
            border.color: Qt.rgba(1, 1, 1, 0.1)
            border.width: 1

            Text {
                text: "〈"
                color: backMouse.pressed || backMouse.containsMouse ? T.Theme.bgMain : T.Theme.textMain
                font.pixelSize: 20; font.bold: true
                anchors.centerIn: parent
                transform: Translate { x: -2 }
            }

            MouseArea {
                id: backMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (profilePage.isCreatingForm) {
                        profilePage.isCreatingForm = false // Annuler la création
                    } else {
                        profilePage.StackView.view.pop() // Retour au menu Véhicule
                    }
                }
            }
        }

        Text {
            text: profilePage.isCreatingForm ? "NOUVEAU VÉHICULE" : "CONFIGURATION VÉHICULES"
            color: T.Theme.textMain
            font.pixelSize: 22; font.bold: true
            font.letterSpacing: 2
            Layout.fillWidth: true
        }

        // Bouton "+ Nouveau" uniquement visible dans la vue liste
        Rectangle {
            width: 120; height: 40; radius: 8
            color: newBtnMouse.pressed ? T.Theme.bgDimmed : T.Theme.main
            visible: !profilePage.isCreatingForm

            Text {
                anchors.centerIn: parent
                text: "+ NOUVEAU"
                color: newBtnMouse.pressed ? T.Theme.textMain : T.Theme.bgMain
                font.bold: true
            }

            MouseArea {
                id: newBtnMouse
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    profilePage.refreshData()
                    // Réinitialisation des champs du formulaire
                    inId.text = ""
                    inName.text = ""
                    inNewConfig.text = ""
                    profilePage.createNewConfig = false
                    profilePage.isCreatingForm = true
                }
            }
        }
    }

    // ====================================================
    // VUE 1 : LISTE DES PROFILS
    // ====================================================
    ListView {
        id: profileView
        visible: !profilePage.isCreatingForm
        // S'adapte pour ne pas passer sous la bannière de redémarrage si elle est visible
        anchors {
            top: header.bottom;
            bottom: restartBanner.visible ? restartBanner.top : parent.bottom;
            left: parent.left; right: parent.right;
            margins: 30; topMargin: 30
        }
        model: profilePage.profileList
        spacing: 12
        clip: true

        delegate: Rectangle {
            width: profileView.width; height: 80
            // Mise en évidence du profil sélectionné pour le prochain redémarrage
            color: modelData === profilePage.pendingProfile ? Qt.rgba(T.Theme.main.r, T.Theme.main.g, T.Theme.main.b, 0.15) : T.Theme.bgDimmed
            radius: 12
            border.color: modelData === profilePage.pendingProfile ? T.Theme.main : Qt.rgba(1, 1, 1, 0.05)
            border.width: modelData === profilePage.pendingProfile ? 2 : 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 20

                Text {
                    text: "🚗"
                    font.pixelSize: 30
                    Layout.alignment: Qt.AlignVCenter
                }

                Column {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 4
                    Text {
                        text: modelData
                        color: T.Theme.textMain
                        font.bold: true
                        font.pixelSize: 18
                    }
                    Text {
                        text: {
                            if (modelData === profilePage.activeProfile && modelData === profilePage.pendingProfile) return "Actif actuel"
                            if (modelData === profilePage.pendingProfile) return "En attente de redémarrage..."
                            return "Disponible"
                        }
                        color: modelData === profilePage.pendingProfile ? T.Theme.main : T.Theme.unselected
                        font.pixelSize: 13
                    }
                }

                // Bouton de sélection
                Rectangle {
                    width: 120; height: 40; radius: 8
                    color: modelData === profilePage.pendingProfile ? "transparent" : T.Theme.main
                    visible: modelData !== profilePage.pendingProfile

                    Text {
                        anchors.centerIn: parent
                        text: "CHOISIR"
                        color: T.Theme.bgMain
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            bridge.setActiveProfile(modelData)
                            profilePage.pendingProfile = modelData // Déclenche l'apparition de la bannière
                        }
                    }
                }
            }
        }
    }

    // ====================================================
    // VUE 2 : FORMULAIRE DE CRÉATION
    // ====================================================
    ScrollView {
        visible: profilePage.isCreatingForm
        anchors { top: header.bottom; bottom: parent.bottom; left: parent.left; right: parent.right; margins: 30; topMargin: 30 }
        clip: true

        ColumnLayout {
            width: parent.width - 20 // Marge pour la barre de défilement
            spacing: 25

            // --- Bloc 1 : Informations générales ---
            Rectangle {
                Layout.fillWidth: true; height: 200
                color: T.Theme.bgDimmed; radius: 12
                border.color: Qt.rgba(1, 1, 1, 0.05)

                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 15

                    Text { text: "IDENTIFIANTS"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 14 }

                    TextField {
                        id: inId
                        Layout.fillWidth: true; height: 45
                        placeholderText: "ID technique (ex: clio_rs_2008)"
                        font.pixelSize: 16
                        color: T.Theme.textMain
                        background: Rectangle { color: T.Theme.bgMain; radius: 8; border.color: Qt.rgba(1, 1, 1, 0.2) }
                    }

                    TextField {
                        id: inName
                        Layout.fillWidth: true; height: 45
                        placeholderText: "Nom d'affichage (ex: Clio 3 RS)"
                        font.pixelSize: 16
                        color: T.Theme.textMain
                        background: Rectangle { color: T.Theme.bgMain; radius: 8; border.color: Qt.rgba(1, 1, 1, 0.2) }
                    }
                }
            }

            // --- Bloc 2 : Fichiers sources ---
            Rectangle {
                Layout.fillWidth: true; height: 280
                color: T.Theme.bgDimmed; radius: 12
                border.color: Qt.rgba(1, 1, 1, 0.05)

                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 15

                    Text { text: "SOURCES DE DONNÉES"; color: T.Theme.unselected; font.bold: true; font.pixelSize: 14 }

                    Text { text: "Matrice CAN :"; color: T.Theme.textMain; font.pixelSize: 16 }
                    ComboBox {
                        id: canCombo
                        Layout.fillWidth: true; height: 45
                        font.pixelSize: 16
                    }

                    // Bascule de configuration (Existant / Nouveau)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 15

                        Text { text: "Configuration :"; color: T.Theme.textMain; font.pixelSize: 16 }

                        Rectangle {
                            Layout.fillWidth: true; height: 35; radius: 8
                            color: !profilePage.createNewConfig ? T.Theme.main : T.Theme.bgMain
                            Text { anchors.centerIn: parent; text: "Existante"; color: !profilePage.createNewConfig ? T.Theme.bgMain : T.Theme.textMain; font.bold: true }
                            MouseArea { anchors.fill: parent; onClicked: profilePage.createNewConfig = false }
                        }

                        Rectangle {
                            Layout.fillWidth: true; height: 35; radius: 8
                            color: profilePage.createNewConfig ? T.Theme.main : T.Theme.bgMain
                            Text { anchors.centerIn: parent; text: "Nouvelle"; color: profilePage.createNewConfig ? T.Theme.bgMain : T.Theme.textMain; font.bold: true }
                            MouseArea { anchors.fill: parent; onClicked: profilePage.createNewConfig = true }
                        }
                    }

                    // Champ dynamique selon le choix
                    ComboBox {
                        id: confCombo
                        visible: !profilePage.createNewConfig
                        Layout.fillWidth: true; height: 45
                        font.pixelSize: 16
                    }

                    TextField {
                        id: inNewConfig
                        visible: profilePage.createNewConfig
                        Layout.fillWidth: true; height: 45
                        placeholderText: "Nom du fichier (ex: config_clio_rs.json)"
                        font.pixelSize: 16
                        color: T.Theme.textMain
                        background: Rectangle { color: T.Theme.bgMain; radius: 8; border.color: Qt.rgba(1, 1, 1, 0.2) }
                    }
                }
            }

            // --- Bouton de validation ---
            Rectangle {
                Layout.fillWidth: true; height: 60; radius: 12
                color: (inId.text !== "" && inName.text !== "") ? T.Theme.main : Qt.rgba(T.Theme.main.r, T.Theme.main.g, T.Theme.main.b, 0.3)

                Text {
                    anchors.centerIn: parent
                    text: "SAUVEGARDER LE VÉHICULE"
                    color: T.Theme.bgMain
                    font.bold: true
                    font.pixelSize: 18
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: inId.text !== "" && inName.text !== ""
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        let finalConf = profilePage.createNewConfig ? inNewConfig.text : confCombo.currentText
                        // Sécurité : ajout auto de l'extension .json si oubliée
                        if (profilePage.createNewConfig && !finalConf.endsWith(".json")) {
                            finalConf += ".json"
                        }

                        let success = bridge.createNewProfile(
                            inId.text,
                            inName.text,
                            canCombo.currentText,
                            finalConf,
                            "save_" + inId.text + ".json"
                        )

                        if(success) {
                            profilePage.refreshData()
                            profilePage.isCreatingForm = false // Retour à la liste
                        }
                    }
                }
            }
        }
    }

    // ====================================================
    // ZONE DE REDÉMARRAGE (Apparaît si changement de profil)
    // ====================================================
    Rectangle {
        id: restartBanner
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: 90
        color: T.Theme.main

        // S'affiche uniquement sur la liste, si un profil différent de l'actuel est choisi
        visible: !profilePage.isCreatingForm && (profilePage.activeProfile !== profilePage.pendingProfile)

        RowLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20

            Column {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                Text { text: "NOUVEAU PROFIL SÉLECTIONNÉ"; color: T.Theme.bgMain; font.bold: true; font.pixelSize: 16 }
                Text { text: "Un redémarrage du tableau de bord est nécessaire."; color: T.Theme.bgMain; font.pixelSize: 13 }
            }

            Rectangle {
                width: 150; height: 45; radius: 8
                color: T.Theme.bgMain

                Text {
                    anchors.centerIn: parent
                    text: "REDÉMARRER"
                    color: T.Theme.main
                    font.bold: true
                    font.pixelSize: 16
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.restartApplication()
                }
            }
        }
    }
}