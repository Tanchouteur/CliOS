import QtQuick
import QtQuick.Controls
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

    Loader {
        id: dashboardLoader
        anchors.fill: parent
        source: Qt.resolvedUrl(StyleManager.dashboardSource)
    }

    NotificationCenter {
        id: notifCenter
        z: 9999 // Toujours au premier plan
    }
}
