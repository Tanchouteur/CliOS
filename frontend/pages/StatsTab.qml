import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Item {
    id: root
    property var trip: bridge.stats !== undefined ? bridge.stats : {}

    // Sécurité anti-division par zéro pour la jauge de roue libre
    property real coastingPercent: (trip.distance_km > 0) ? (trip.coasting_km / trip.distance_km) : 0.0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // ─── EN-TÊTE : TITRE ET STATUT ───
        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "STATISTIQUES DU TRAJET"
                color: T.Theme.textMain
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
                Layout.alignment: Qt.AlignLeft
            }

            Item { Layout.fillWidth: true } // Espaceur invisible

            // Indicateur d'enregistrement actif
            Row {
                spacing: 8
                visible: trip.is_active === true
                Layout.alignment: Qt.AlignRight

                Rectangle {
                    width: 12; height: 12; radius: 6
                    color: T.Theme.danger
                    anchors.verticalCenter: parent.verticalCenter

                    SequentialAnimation on opacity {
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.2; duration: 800 }
                        NumberAnimation { to: 1.0; duration: 800 }
                    }
                }
                Text {
                    text: "Enregistrement..."
                    color: T.Theme.danger
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // ─── CARTE 1 : BILAN GLOBAL (Pleine largeur) ───
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            color: T.Theme.bgDimmed
            radius: 12
            border.color: Qt.rgba(1, 1, 1, 0.1)
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 20

                // Distance
                Column {
                    Layout.fillWidth: true
                    Text { text: "DISTANCE"; color: T.Theme.unselected; font.pixelSize: 14 }
                    Row {
                        Text { text: trip.distance_km !== undefined ? trip.distance_km.toFixed(1) : "0.0"; color: T.Theme.textMain; font.pixelSize: 36; font.bold: true }
                        Text { text: " km"; color: T.Theme.main; font.pixelSize: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 4 }
                    }
                }

                // Ligne de séparation verticale
                Rectangle { width: 1; Layout.fillHeight: true; color: Qt.rgba(1, 1, 1, 0.1) }

                // Essence
                Column {
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Text { text: "CARBURANT CONSOMMÉ"; color: T.Theme.unselected; font.pixelSize: 14 }
                    Row {
                        Text { text: trip.session_fuel_l !== undefined ? trip.session_fuel_l.toFixed(2) : "0.00"; color: T.Theme.textMain; font.pixelSize: 36; font.bold: true }
                        Text { text: " L"; color: T.Theme.mainLight; font.pixelSize: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 4 }
                    }
                }

                Column {
                    Layout.fillWidth: true
                    Layout.leftMargin: 0
                    Text { text: "PRIX DU TRAJET"; color: T.Theme.unselected; font.pixelSize: 14 }
                    Row {
                        Text {
                            text: trip.session_cost !== undefined ? trip.session_cost.toFixed(2) : "0.00"
                            color: T.Theme.textMain
                            font.pixelSize: 36
                            font.bold: true
                        }

                        Text { text: " €"; color: T.Theme.mainLight; font.pixelSize: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 4 }
                    }
                }


            }
        }

        // ─── GRILLE BASSE : ÉCO & PERF ───
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            columnSpacing: 20

            // CARTE 2 : ÉCO-CONDUITE (Gauche)
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: T.Theme.bgDimmed
                radius: 12
                border.color: Qt.rgba(1, 1, 1, 0.1)
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 15

                    Text { text: "ÉCO-EFFICIENCE"; color: T.Theme.unselected; font.pixelSize: 14; font.bold: true }

                    // Agressivité
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Pression pédale moyenne :"; color: T.Theme.textMain; font.pixelSize: 16; Layout.fillWidth: true }
                        Text { text: (trip.aggressivity_pct !== undefined ? trip.aggressivity_pct.toFixed(0) : "0") + " %"; color: T.Theme.mainLight; font.pixelSize: 18; font.bold: true }
                    }

                    // Roue libre
                    Column {
                        Layout.fillWidth: true
                        spacing: 8
                        RowLayout {
                            width: parent.width
                            Text { text: "Roue libre (sans accélérer) :"; color: T.Theme.textMain; font.pixelSize: 16; Layout.fillWidth: true }
                            Text { text: (trip.coasting_km !== undefined ? trip.coasting_km.toFixed(1) : "0.0") + " km"; color: T.Theme.mainLight; font.pixelSize: 18; font.bold: true }
                        }

                        // Petite jauge visuelle (Progress Bar custom)
                        Rectangle {
                            width: parent.width
                            height: 6
                            radius: 3
                            color: Qt.rgba(0, 0, 0, 0.5) // Fond de la jauge

                            Rectangle {
                                width: parent.width * root.coastingPercent
                                height: parent.height
                                radius: 3
                                color: T.Theme.info // Couleur bleue/verte pour l'éco

                                Behavior on width { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true } // Pousse le contenu vers le haut
                }
            }

            // CARTE 3 : MÉCANIQUE (Droite)
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: T.Theme.bgDimmed
                radius: 12
                border.color: Qt.rgba(1, 1, 1, 0.1)
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 25

                    Text { text: "MÉCANIQUE"; color: T.Theme.unselected; font.pixelSize: 14; font.bold: true }

                    // RPM
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Régime moteur moyen :"; color: T.Theme.textMain; font.pixelSize: 16; Layout.fillWidth: true }
                        Text { text: (trip.avg_rpm !== undefined ? trip.avg_rpm : "0") + " RPM"; color: T.Theme.mainLight; font.pixelSize: 18; font.bold: true }
                    }

                    // Shift Time
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Temps de passage rapport :"; color: T.Theme.textMain; font.pixelSize: 16; Layout.fillWidth: true }
                        Text { text: (trip.shift_time_sec !== undefined ? trip.shift_time_sec.toFixed(2) : "0.00") + " s"; color: T.Theme.mainLight; font.pixelSize: 18; font.bold: true }
                    }

                    Item { Layout.fillHeight: true } // Pousse le contenu vers le haut
                }
            }
        }
    }
}