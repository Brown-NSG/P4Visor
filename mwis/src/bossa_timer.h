//****************************************************
//
// BossaTimer (measures the algorithm's elapsed time)
//
//****************************************************

#ifndef bossa_timer_h
#define bossa_timer_h


#ifndef BOSSA_RUSAGE
#ifndef BOSSA_CLOCK
#ifndef BOSSA_HTIME

#ifdef WIN32
	#define BOSSA_CLOCK
#else 
	#include <sys/time.h>
	#ifdef __GLIBC__
		#define BOSSA_RUSAGE
	#else 
		#define BOSSA_HTIME
	#endif
#endif

#endif
#endif
#endif 


//#define BOSSA_RUSAGE
//#define BOSSA_CLOCK
//#define BOSSA_HTIME

#ifdef BOSSA_RUSAGE
#include <sys/resource.h>
#endif

class BossaTimer {

	private:
		bool running; //is it running now? (false -> paused)
		double base_time; //time of previous runs since last reset
		double max_time;  //reference time  

	#ifdef BOSSA_CLOCK 
		double getUserTime();
		double start_time;
	#endif

	#ifdef BOSSA_HTIME
		long start_time, end_time;
	#endif

	#ifdef BOSSA_RUSAGE
		struct rusage ru;
		struct timeval start_time, end_time, sample_time;
	#endif

		double getElapsedTime(); //time since last resume/start (does not include base_time)
		void startTiming();

		
		void setBaseTime (double bt); 

	public:
		//BossaTimer (); //reset
		BossaTimer (bool start=false);
		double getTime(); //return current time
		double pause();   //pause and return current time
		double resume();  //continue if paused, start if reset (return time before resuming)
		double start();   //reset and resume (return time before reset)
		double reset();   //reset timer and pause (at zero) (return time before reset)

		void setMaxTime (double mt);
		double getMaxTime();
		double getTimeToExpire(); 
		bool isTimeExpired ();    
};

#endif

