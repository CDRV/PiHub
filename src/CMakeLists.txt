find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Core LinguistTools)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Core LinguistTools WebSockets Network)

set(PiHubApp_includes
    PiHubApp.h
)

set(PiHubApp_srcs
    PiHubApp.cpp
    main.cpp
)

#This will generate moc_* for Qt
qt_wrap_cpp(PiHubAppn_moc_srcs ${PiHubApp_includes})


add_executable(PiHubApp ${PiHubApp_includes} ${PiHubApp_srcs} ${PiHubApp_moc_srcs})
target_link_libraries(PiHubApp PUBLIC Qt${QT_VERSION_MAJOR}::Core Qt${QT_VERSION_MAJOR}::WebSockets Qt${QT_VERSION_MAJOR}::Network)
target_include_directories(PiHubApp PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

