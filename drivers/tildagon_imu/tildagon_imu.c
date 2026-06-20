
#include "esp_err.h"
#include "esp_log.h"
#include "py/mperrno.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "st3m_imu.h"
#include "lsm6ds3.h"

#include "tildagon_imu.h"

typedef enum
{ 
    ST3M,
    LSM6DS3,
    /* add new imu type here */
    MAX_DEVICES,
} which_imu_t;

typedef void (*stepfuncptr_t) ( uint32_t* steps );
typedef void (*stepresetfuncptr_t) ( void );
typedef void (*tempfuncptr_t) ( float* temperature );
typedef int  (*i2cfuncptr_t) ( uint8_t reg_addr, uint8_t *reg_data, uint8_t len );

void imu_run( void* data );

i2cfuncptr_t i2c_write[MAX_DEVICES] =
{
    /* ST3M */    st3m_imu_write,
    /* LSM6DS3 */ lsm6ds3_write,
};

i2cfuncptr_t i2c_read[MAX_DEVICES] =
{
    /* ST3M */    st3m_imu_read,
    /* LSM6DS3 */ lsm6ds3_read,
};

updatefuncptr_t update[MAX_DEVICES] = 
{
    /* ST3M */    st3m_imu_task,
    /* LSM6DS3 */ lsm6ds3_task,
};

sensorfuncptr_t accel_read[MAX_DEVICES] =
{
    /* ST3M */     st3m_imu_read_acc_mps,
    /* LSM6DS3 */  lsm6ds3_read_acc_mps,
};

sensorfuncptr_t gyro_read[MAX_DEVICES] =
{
    /* ST3M */     st3m_imu_read_gyro_dps,
    /* LSM6DS3 */  lsm6ds3_read_gyro_dps,
};

stepfuncptr_t step_read[MAX_DEVICES] =
{
    /* ST3M */     st3m_imu_read_steps,
    /* LSM6DS3 */  lsm6ds3_read_steps,
};

stepresetfuncptr_t step_reset[MAX_DEVICES] =
{
    /* ST3M */     st3m_imu_reset_steps,
    /* LSM6DS3 */  NULL,  /* resets its count on each read, no explicit reset */
};

tempfuncptr_t temp_read[MAX_DEVICES] =
{
    /* ST3M */     st3m_imu_read_temperature,
    /* LSM6DS3 */  lsm6ds3_read_temperature,
};

static sensorfuncptr_t compass_readptr = NULL;
static updatefuncptr_t compass_funcptr = NULL;

static char st3m_id[]  = "bmi270";
static char lsm6ds3_id[]  = "lsm6ds3";
static char* id_list[MAX_DEVICES] = 
{
    /* ST3M */     st3m_id,
    /* LSM6DS3 */  lsm6ds3_id,
};

which_imu_t imu = MAX_DEVICES;

void tildagon_imu_init( void )
{
    if ( st3m_imu_init() == ESP_OK )
    {
        imu = ST3M;
    }
    else if ( lsm6ds3_init() == ESP_OK )
    {
        imu = LSM6DS3;
    }
    
    if ( imu < MAX_DEVICES )
    {
        /* create task */
        xTaskCreate( imu_run, "imu", 4096, NULL, configMAX_PRIORITIES - 2, NULL);
    }
}

void tildagon_imu_acc_read( float* x, float*y, float*z )
{
    if ( imu < MAX_DEVICES)
    {
        ( *accel_read[imu] )( x, y, z );
    }
    else
    {
        *x = 1.0F;
        *y = 1.0F;
        *z = 1.0F;
    }
}

void tildagon_imu_gyro_read( float* x, float*y, float*z )
{
    if ( imu < MAX_DEVICES)
    {
        ( *gyro_read[imu] )( x, y, z );
    }
    else
    {
        *x = 1.0F;
        *y = 1.0F;
        *z = 1.0F;
    }
}

void tildagon_imu_step_counter_read( uint32_t* steps )
{
    if ( imu < MAX_DEVICES)
    {
        ( *step_read[imu] )( steps );
    }
    else
    {
        *steps = 0xFFFFFFFF;
    }
}

void tildagon_imu_step_counter_reset( void )
{
    if ( imu < MAX_DEVICES && step_reset[imu] != NULL )
    {
        ( *step_reset[imu] )();
    }
}

void tildagon_imu_temperature_read( float* temperature )
{
    if ( imu < MAX_DEVICES)
    {
        ( *temp_read[imu] )( temperature );
    }
    else
    {
        *temperature = -274.0F;
    }
}

char* tildagon_imu_get_id( void )
{
    if ( imu < MAX_DEVICES )
    {
        return id_list[imu];
    }
    else
    {
        static char no_device[] = "no device present";
        return no_device;
    }
}

int tildagon_imu_write( uint8_t address, uint8_t length, uint8_t* buffer )
{
    if ( imu < MAX_DEVICES )
    {
        return ( *i2c_write[imu] )(address, buffer, length );
    }
    else
    {
        return -MP_ENODEV;
    }
}

int tildagon_imu_read( uint8_t address, uint8_t length, uint8_t* buffer )
{
    if ( imu < MAX_DEVICES )
    {
        return ( *i2c_read[imu] )(address, buffer, length );
    }
    else
    {
        return -MP_ENODEV;
    }
}

void tildagon_imu_register_compass( updatefuncptr_t compass_update, sensorfuncptr_t compass_read )
{
    compass_funcptr = compass_update;
    compass_readptr = compass_read;
}

void tildagon_imu_compass_read( float* x, float*y, float*z )
{
    if ( compass_readptr != NULL )
    {
        compass_readptr( x, y, z );
    }
}

void imu_run( void* data )
{
    TickType_t last_wake = xTaskGetTickCount();
    while (1) 
    {
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(10));  // 100 Hz

        update[imu]();
        if ( compass_funcptr != NULL )
        {
            compass_funcptr();
        }
    }
}
