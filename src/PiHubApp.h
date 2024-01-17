#ifndef _PIHUBAPP_H_
#define _PIHUBAPP_H_

#include <QCoreApplication>

class PiHubApp : public QCoreApplication
{
    Q_OBJECT
public:
    PiHubApp(int &argc, char **argv);
    ~PiHubApp();
};


#endif
