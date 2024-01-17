find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Core LinguistTools)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Core LinguistTools WebSockets Network HttpServer)

set(PiHubApp_includes
    AppleWatchHttpServer.h
    PiHubApp.h
)

set(PiHubApp_srcs
    AppleWatchHttpServer.cpp
    PiHubApp.cpp
    main.cpp
)

set(PiHubApp_qrcs
    PiHubApp.qrc
)

#This will generate moc_* for Qt
qt_wrap_cpp(PiHubApp_moc_srcs ${PiHubApp_includes})


add_executable(PiHubApp ${PiHubApp_includes} ${PiHubApp_srcs} ${PiHubApp_qrcs} ${PiHubApp_moc_srcs})
target_link_libraries(PiHubApp PUBLIC Qt${QT_VERSION_MAJOR}::Core Qt${QT_VERSION_MAJOR}::WebSockets Qt${QT_VERSION_MAJOR}::Network Qt${QT_VERSION_MAJOR}::HttpServer)
target_include_directories(PiHubApp PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

