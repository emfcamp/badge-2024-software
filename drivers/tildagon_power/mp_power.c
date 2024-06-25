#include "py/obj.h"
#include "py/runtime.h"
#include "py/builtin.h"
#include <stdint.h>
#include "tildagon_power.h"

/* 
    minimum input voltage for step down at max (4A) load. 
    minimum input voltage = ( Rl(DCR) + Rdson ) * max current + output voltage
    (0.078ohms * 4.0A) + 3.3V = 3.6V 
    most users won't use 4A so badge will run lower than this so use 3.5V as minimum.
*/
#define VBAT_DIS_MAX 4.14F
#define VBAT_DIS_MIN 3.5F
#define VBAT_CHG_MAX 4.2F
#define VBAT_CHG_MIN 3.6F
#define IBAT_TERM 0.064F
#define VBAT_CI_PERCENT 85.0F

static mp_obj_t power_enable5V( mp_obj_t a_obj )
{
    bool enable = (bool)mp_obj_get_int(a_obj);
    tildagon_power_enable_5v( enable );
    return MP_OBJ_NEW_SMALL_INT(1);
}

static MP_DEFINE_CONST_FUN_OBJ_1( enable5V_obj, power_enable5V);

static mp_obj_t power_Off( void )
{
    tildagon_power_off();
    return MP_OBJ_NEW_SMALL_INT(1);
}

static MP_DEFINE_CONST_FUN_OBJ_0( Off_obj, power_Off);

static mp_obj_t power_Vbus( void ) 
{
    bq_update_state( &pmic );
    return mp_obj_new_float(pmic.vbus);
}

static MP_DEFINE_CONST_FUN_OBJ_0( Vbus_obj, power_Vbus);

static mp_obj_t power_Vsys( void ) 
{
    bq_update_state( &pmic );
    return mp_obj_new_float(pmic.vsys);
}

static MP_DEFINE_CONST_FUN_OBJ_0( Vsys_obj, power_Vsys);

static mp_obj_t power_Vbat( void ) 
{
    bq_update_state( &pmic );
    return mp_obj_new_float(pmic.vbat);
}

static MP_DEFINE_CONST_FUN_OBJ_0( Vbat_obj, power_Vbat);

static mp_obj_t power_Icharge( void ) 
{
    bq_update_state( &pmic );
    return mp_obj_new_float(pmic.ichrg);
}

static MP_DEFINE_CONST_FUN_OBJ_0( Icharge_obj, power_Icharge);

static mp_obj_t power_BatteryLevel( void ) 
{
    bq_update_state( &pmic );
    float level = 0.0F;
    if( ( ( pmic.status & BQ_CHARGE_STAT_MASK ) == BQ_NOTCHARGING )
     || ( ( pmic.status & BQ_CHARGE_STAT_MASK ) == BQ_TERMINATED ) )
    {
        level = ( ( pmic.vbat-VBAT_DIS_MIN ) / ( VBAT_DIS_MAX- VBAT_DIS_MIN ) ) * 100.0F;
    }
    else
    {
        float max_current = 1.536F;
        float vbat_cv_percent = 20.0F;
        float vbat_ci_percent = 100.0F - vbat_cv_percent;
        if ( usb_in.fusb.input_current_limit == 1500U )
        {
            max_current = 1.3F;
            vbat_cv_percent = 17.0F;
            vbat_ci_percent = 100.0F - vbat_cv_percent;
        }
        else if ( usb_in.fusb.input_current_limit == 500 )
        {
            max_current = 0.4F;
            vbat_cv_percent = 2.0F;
            vbat_ci_percent = 100.0F - vbat_cv_percent;
        }
        if ( pmic.vbat < VBAT_CHG_MAX )
        {
            level = ( ( pmic.vbat-VBAT_CHG_MIN ) / ( VBAT_CHG_MAX - VBAT_CHG_MIN ) ) * vbat_ci_percent;
        }
        else
        {    
            level =  100.0F - ( ( pmic.ichrg / ( max_current - IBAT_TERM ) ) * vbat_cv_percent );
        }
    }    
    if ( level > 100.0F )
    {
        level = 100.0F;
    }
    else if ( level < 0.0F )
    {
        level = 0.0F;
    }
    return mp_obj_new_float(level);
}

static MP_DEFINE_CONST_FUN_OBJ_0( BatteryLevel_obj, power_BatteryLevel);

static mp_obj_t power_BatteryChargeState( void ) 
{
    mp_obj_t charge_state = mp_obj_new_str( "Not Charging", 12 );
    bq_update_state( &pmic );
    switch ( pmic.status & BQ_CHARGE_STAT_MASK )
    {
        case BQ_NOTCHARGING:
        {
            charge_state = mp_obj_new_str( "Not Charging", 12 );
            break;
        }
        case BQ_PRECHARGING:
        {
            charge_state = mp_obj_new_str( "Pre-Charging", 12 );
            break;
        }
        case BQ_FASTCHARGING:
        {
            charge_state = mp_obj_new_str( "Fast Charging", 13 );
            break;
        }
        case BQ_TERMINATED:
        {
            charge_state = mp_obj_new_str( "Terminated", 10 );
            break;
        }
    }
    return charge_state;
}

static MP_DEFINE_CONST_FUN_OBJ_0( BatteryChargeState_obj, power_BatteryChargeState);

static mp_obj_t power_SupplyCapabilities( void ) 
{
    mp_obj_t capabilities = mp_obj_new_list(0, NULL);
    if ( usb_in.pd.number_of_pdos > 0 )
    {
        for ( uint8_t i = 0; i < usb_in.pd.number_of_pdos; i++ )
        {
            mp_obj_t tuple[3];
            switch ( usb_in.pd.pdos[i].fixed.pdo_type )
            {
                case 0: /* fixed supply */
                {
                    tuple[0] = mp_obj_new_str( "fixed", 5 );
                    tuple[1] = mp_obj_new_int( usb_in.pd.pdos[i].fixed.max_current * 10 );
                    tuple[2] = mp_obj_new_int( ( usb_in.pd.pdos[i].fixed.voltage * 50 ) / 1000 );
                    mp_obj_t capability = mp_obj_new_tuple(3, tuple);
                    mp_obj_list_append(capabilities, capability);
                    break;
                }
                case 1: /* battery */
                {
                    tuple[0] = mp_obj_new_str( "battery", 7 );
                    tuple[1] = mp_obj_new_int( ( usb_in.pd.pdos[i].battery.min_volt * 50 ) / 1000 );
                    tuple[2] = mp_obj_new_int( ( usb_in.pd.pdos[i].battery.max_volt * 50 ) / 1000 );
                    mp_obj_t capability = mp_obj_new_tuple(3, tuple);
                    mp_obj_list_append(capabilities, capability);
                    break;
                }
                case 2: /* non battery variable supply */
                {
                    tuple[0] = mp_obj_new_str( "variable", 8 );
                    tuple[1] = mp_obj_new_int( usb_in.pd.pdos[i].variable.max_current * 10 );
                    tuple[2] = mp_obj_new_int( ( usb_in.pd.pdos[i].variable.max_voltage * 50 ) / 1000 );
                    mp_obj_t capability = mp_obj_new_tuple(3, tuple);
                    mp_obj_list_append(capabilities, capability);
                    break;
                }
                default:
                {
                    /* don't add anything to the list */
                }
           }
        }
    }
    else
    {
        /* do something for non pd supplies */
        
        if ( usb_in.fusb.status & FUSB_STATUS_VBUSOK_MASK )
        {
            bq_update_state( &pmic );
            mp_obj_t tuple[3];
            tuple[0] = mp_obj_new_str( "non-pd", 6 );
            tuple[1] = mp_obj_new_int( usb_in.fusb.input_current_limit );
            tuple[2] = mp_obj_new_int( (int)pmic.vbus );
            mp_obj_t capability = mp_obj_new_tuple(3, tuple);
            mp_obj_list_append(capabilities, capability);
        }
        else
        {
            mp_obj_t tuple[3];
            tuple[0] = mp_obj_new_str( "disconnected", 12 );
            tuple[1] = mp_obj_new_str( "0", 1 );
            tuple[2] = mp_obj_new_str( "0", 1 );
            mp_obj_t capability = mp_obj_new_tuple(3, tuple);
            mp_obj_list_append(capabilities, capability);
        }
    }
    return capabilities;
}

static MP_DEFINE_CONST_FUN_OBJ_0( SupplyCapabilities_obj, power_SupplyCapabilities);

static mp_obj_t power_Fault( void ) 
{
    mp_obj_t faults = mp_obj_new_dict( 3 );
    if ( pmic.fault & BQ_FAULT_BATTERY_MASK )
    {
        mp_obj_dict_store( faults, mp_obj_new_str( "Battery", 7 ), mp_obj_new_str( "Battery Over Voltage", 20 ) );
    }
    else 
    {
        mp_obj_dict_store( faults, mp_obj_new_str( "Battery", 7 ), mp_obj_new_str( "Normal", 6 ) );
    }
    if ( pmic.fault & BQ_FAULT_BOOST_MASK )
    {
        mp_obj_dict_store( faults, mp_obj_new_str( "Boost", 5 ), mp_obj_new_str( "Overloaded or low battery", 25 ) );
    }
    else 
    {
        mp_obj_dict_store( faults, mp_obj_new_str( "Boost", 5 ), mp_obj_new_str( "Normal", 6 ) );
    }
    switch ( pmic.fault & BQ_FAULT_CHARGE_MASK )
    {
        case BQ_FAULT_INPUT:
        {
            mp_obj_dict_store( faults, mp_obj_new_str( "Charge", 6 ), mp_obj_new_str( "Input Fault", 11 ) );
            break;
        }
        case BQ_FAULT_TIMER:
        {
            mp_obj_dict_store( faults, mp_obj_new_str( "Charge", 6 ), mp_obj_new_str( "Safety timer expired", 20 ) );
            break;
        }
        case BQ_FAULT_THERMAL: /* thermal shutdown ignored */
        case BQ_FAULT_NONE:
        default:
        {
            mp_obj_dict_store( faults, mp_obj_new_str( "Charge", 6 ), mp_obj_new_str( "Normal", 6 ) );
            break;
        }      
    }
    return faults;
}

static MP_DEFINE_CONST_FUN_OBJ_0( Fault_obj, power_Fault);

static const mp_rom_map_elem_t power_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_power) },
    { MP_ROM_QSTR(MP_QSTR_Enable5V), MP_ROM_PTR(&enable5V_obj) },
    { MP_ROM_QSTR(MP_QSTR_Off), MP_ROM_PTR(&Off_obj) },
    { MP_ROM_QSTR(MP_QSTR_Vin), MP_ROM_PTR(&Vbus_obj) },
    { MP_ROM_QSTR(MP_QSTR_Vsys), MP_ROM_PTR(&Vsys_obj) },
    { MP_ROM_QSTR(MP_QSTR_Vbat), MP_ROM_PTR(&Vbat_obj) },
    { MP_ROM_QSTR(MP_QSTR_Icharge), MP_ROM_PTR(&Icharge_obj) },
    { MP_ROM_QSTR(MP_QSTR_BatteryLevel), MP_ROM_PTR(&BatteryLevel_obj) },
    { MP_ROM_QSTR(MP_QSTR_BatteryChargeState), MP_ROM_PTR(&BatteryChargeState_obj) },
    { MP_ROM_QSTR(MP_QSTR_SupplyCapabilities), MP_ROM_PTR(&SupplyCapabilities_obj) },
    { MP_ROM_QSTR(MP_QSTR_Fault), MP_ROM_PTR(&Fault_obj) },
};

static MP_DEFINE_CONST_DICT(power_module_globals, power_module_globals_table);

const mp_obj_module_t power_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&power_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_power, power_user_cmodule);
