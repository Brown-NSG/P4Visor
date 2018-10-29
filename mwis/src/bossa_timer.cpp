//******************************************************
//
// BossaTimer (measures the algorithm's execution time)
//
//******************************************************

#include "bossa_timer.h"

#define INFINITE_TIME 10e100

//-----------------------------
// Generic functions
//-----------------------------

/*
BossaTimer::BossaTimer () {
	base_time = 0.0;
	max_time = 0.0;
	running = false;
}*/

BossaTimer::BossaTimer (bool s) {
	base_time = 0.0;
	max_time = 0.0;
	if (s) start();
	else running = false;
}

double BossaTimer::getTime() {
	if (running) return (getElapsedTime() + base_time);
	else return base_time;
}

double BossaTimer::start() {
	double current = getTime();
	base_time = 0.0;
	startTiming();
	running = true;
	return current;
}

void BossaTimer::setMaxTime (double mt) {max_time = mt;}
double BossaTimer::getMaxTime () {return max_time;}

bool BossaTimer::isTimeExpired () {
	if (getMaxTime() == 0) return false;
	bool time_expired = (getTime() >= getMaxTime());
	return time_expired;
}

double BossaTimer::getTimeToExpire () { //may be negative!
	if (getMaxTime() == 0) return INFINITE_TIME;
	else return (getTime() - getMaxTime());
}

void BossaTimer::setBaseTime (double bt) {base_time = bt;}

double BossaTimer::reset() {
	double current = getTime();
	running = false;
	base_time = 0.0;
	return current;
}

double BossaTimer::pause() {
	base_time = getTime();
	running = false;
	return base_time;
}

double BossaTimer::resume() {
	if (running) return getTime();
	else {
		running = true;
		startTiming();
		return base_time;
	}
}

//--------------------------
// BOSSA_RUSAGE
//--------------------------

#ifdef BOSSA_RUSAGE

void BossaTimer::startTiming() {
  getrusage(RUSAGE_SELF, &ru);
  start_time = ru.ru_utime;
}

//time elapsed since startTiming was called
double BossaTimer::getElapsedTime() {
  double t;
  getrusage(RUSAGE_SELF, &ru);
  end_time = ru.ru_utime;
  if (end_time.tv_usec < start_time.tv_usec){
    end_time.tv_usec += 1000000;
    end_time.tv_sec -= 1;
  }
  t = 100.0*(double)(end_time.tv_sec - start_time.tv_sec) + (double)(end_time.tv_usec - start_time.tv_usec) / (double)10000.0;
  return ((double)t/(double)100);
}

#endif


//--------------
// BOSSA_CLOCK
//--------------

#ifdef BOSSA_CLOCK

#include <stdio.h>
#include <time.h>

void BossaTimer::startTiming() {start_time = getUserTime();}
double BossaTimer::getElapsedTime() {
	return (getUserTime() - start_time);
}
double BossaTimer::getUserTime() {
	double msecs = (double) clock() / CLOCKS_PER_SEC;
	if (msecs > 0) return msecs; 
	else return 0.0; //sometimes msecs is -0.000 (go figure...)
}

#endif


//--------------
// BOSSA_HTIME
//--------------

#ifdef BOSSA_HTIME

#include <sys/time.h>
void BossaTimer::startTiming() {start_time = (long)gethrvtime();}
double BossaTimer::getElapsedTime() {
	return (double)(gethrvtime()-start_time)/(double)10e8;
}
#endif

