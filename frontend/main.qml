import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "style"
import "components"
import "state" as S

ApplicationWindow {
    id: appWindow
    property string version: S.UiState.systemVersion
    visible: true
    width: 1920
    height: 720
    title: "CliOS v" + version

    visibility: Window.FullScreen
    flags: Qt.FramelessWindowHint | Qt.Window | Qt.MSWindowsFixedSizeDialogHint

    color: Theme.bgMain

    AppShell { id: shell; anchors.fill: parent }

    // Raccourci clavier de secours pour le dev / test (F12 ou Ctrl+M)
    Item {
        focus: true
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_F12 || (event.key === Qt.Key_M && (event.modifiers & Qt.ControlModifier))) {
                shell.openRoute("maintenance")
                event.accepted = true
            }
        }
    }
}
