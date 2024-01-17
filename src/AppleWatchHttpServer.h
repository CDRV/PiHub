#ifndef APPLEWATCHHTTPSERVER_H
#define APPLEWATCHHTTPSERVER_H

#include <QObject>
#include <QHttpServer>

class AppleWatchHttpServer : public QObject
{
    Q_OBJECT
public:
    explicit AppleWatchHttpServer(quint16 port, QObject *parent = nullptr);

signals:

protected:
    QHttpServer *m_httpServer;
    quint16 m_port;

};

#endif // APPLEWATCHHTTPSERVER_H
