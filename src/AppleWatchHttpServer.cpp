#include "AppleWatchHttpServer.h"

#include <QHostAddress>


AppleWatchHttpServer::AppleWatchHttpServer(quint16 port, QObject *parent)
    : QObject{parent}, m_httpServer{new QHttpServer{this}}, m_port{port}
{
    m_httpServer->listen(QHostAddress::Any, m_port);

}

