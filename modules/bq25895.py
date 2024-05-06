"""
BQ25895 power management ic driver in MicroPython.

The driver supports basic read write access with some helpers

This is a work in progress.

"""

from micropython import const
from collections import namedtuple


class charge_time:
    Hrs5 = 0x00
    Hrs8 = 0x02
    Hrs12 = 0x04
    Hrs20 = 0x06


class wdttime:
    Disable = 0x00
    secs40 = 0x10
    secs80 = 0x20
    secs160 = 0x30


class bq25895:
    """
    BQ25895 driver class to allow access to registers

    Args:
        i2c_instance (I2C)

    Attributes:
        input_Ilim                  register entry for input current limit set by user or input source detection, range 100-3250mA, 50mA resolution
        Ilim_pin                    register entry to enable or disable the current limit pin
        enable_HiZ                  register entry to put the Vbus input into High impedance mode
        input_voltage_limit_offset  register entry for the input voltage limit offset, range 0-3100mV 100mV resolution
        auto_dpdm                   register entry for automatic D+D- or PSEL detection
        input_current_optimiser     register entry to enable input current optimiser
        boost_frequency             register entry to set the boost converter frequency, 0 = 1.5MHz 1 = 500kHz(default)
        conversion_rate             register entry to enable the 1Hz sampling of ADCs
        conversion_start            register entry to start a single conversion
        min_Vsys                    register entry to set the minimum system voltage limit range 3-3.7V resolution 0.1
        charge_enable               register entry to enable the charge
        otg_boost                   register entry to enable the boost converter
        watchdog_reset              register entry to reset the watchdog timer
        battery_load                register entry to enable the battery load
        charge_Ilim                 register entry to set the fast charge current limit 0-5956mA 64mA resolution
        enable_pulse_control        register entry to enable the current pulse control
        termination_current         register entry for the termination current limit 64-1024mA, 64mA resolution
        precharge_current           register entry for the precharge current limit 64-1024mA, 64mA resolution
        fast_charge_timer           register entry for the fast charge timer setting, see charge_time for steps
        charge_safety_timer_enable  register entry to enable the charging safety timer
        watchdog_timer_setting      register entry for the watchdog timer setting, see wdttime for steps
        status_led_disable          register entry to disable the status LED
        enable_termination          register entry to enable charge termination
        pulse_control_down          register entry for Current pulse control voltage down enable
        pulse_control_up            register entry for Current pulse control voltage up enable
        batfet_reset                register entry for BATFET full system reset enable
        batfet_delay_off            register entry to enable a small delay before disabling the BATFET
        batfet_disable              register entry to disable the BATFET
        timer_slowdown              register entry to slow safety timer during dynamic power management
        force_ICO                   register entry register entry to force start input current optimisation
        boost_setpoint              register entry for the boost target voltage 4.55-5.126V resolution 0.064V
        Vsys_status                 register entry for Vsys regulation status
        USB_input_status            register entry for USB input status
        power_good_status           register entry for power good status
        charge_status               register entry for charging status
        Vbus_status                 register entry for Vbus status
        battery_fault               register entry for battery fault
        charge_fault                register entry for charge fault
        boost_fault                 register entry for boost converter fault
        watchdog_fault              register entry for watchdog fault
        absolute_VINDPM_threshold   register entry for absolute VINDPM threshold
        force_abolute_threshold     register entry to use relative or absolute VINDPM threshold
        battery_voltage             register entry for the Battery voltage ADC 2.304-4.48V resolution 0.02V
        system_voltage              register entry for the system voltage ADC 2.304-4.48V resolution 0.02V
        Vbus_voltage                register entry for the Vbus voltage ADC 2.6-15.3V resolution 0.1V
        Vbus_good                   register entry for the Vbus good status
        charge_current              register entry for the Charge current ADC 0-6350mA resolution 50mA
        DPM_current_limit           register entry for the input current limit in effect while input current optimiser is enabled 100-3250mA resolution 50mA
        IINDPM_status               register entry for IINDPM status
        VINDPM_status               register entry for VINDPM status
        ICO_status                  register entry For the Input current optimiser status
        register_reset              register entry to reset the registers

    """

    def __init__(self, i2c_instance):
        self.i2c = i2c_instance

    # address
    ADDRESS = const(0x6A)

    Register = namedtuple("Register", ["register", "mask", "position"])
    ScaledRegister = namedtuple(
        "ScaledRegister", ["register", "mask", "position", "scaling", "offset"]
    )

    # reg 00
    # input current limit, changed by input source type detection default 500mA
    input_Ilim = ScaledRegister(0x00, 0x3F, 0, 50, 100)
    # ILim pin enable/disable
    Ilim_pin = Register(0x00, 0x40, 6)
    enable_HiZ = Register(0x00, 0x80, 7)
    # reg 01
    # boost temperature threshold not used
    # input voltage limit
    input_voltage_limit_offset = ScaledRegister(0x01, 0x1F, 0, 100, 0)
    # reg 02
    # auto_dpdm = Register( 0x02, 0x01, 0 )
    # the following use D+/D- to detect input and these are not connected
    # force_dpdm = Register(0x02, 0x02, 1 )
    # max_charge_adapter = Register( 0x02, 0x04, 2 )
    # hv_dcp = Register( 0x02, 0x08, 3 )
    input_current_optimiser = Register(0x02, 0x10, 4)
    boost_frequency = Register(0x02, 0x20, 5)
    conversion_rate = Register(0x02, 0x40, 6)
    conversion_start = Register(0x02, 0x80, 7)
    # reg 03
    min_Vsys = ScaledRegister(0x03, 0x0E, 1, 3.0, 0.1)
    charge_enable = Register(0x03, 0x10, 4)
    otg_boost = Register(0x03, 0x20, 5)
    watchdog_reset = Register(0x03, 0x40, 6)
    battery_load = Register(0x03, 0x80, 7)
    # reg 04
    # The battery is a 2000mAh which is the default Charge current limit
    # charge_Ilim = ScaledRegister( 0x04, 0x7F, 0, 64, 0 )
    # PD being handled by FUSB
    # enable_pulse_control = Register( 0x04, 0x80, 7 )
    # reg 05
    # defaults for these are ok.
    # termination_current = ScaledRegister( 0x05, 0x0F, 0, 64, 64 )
    # precharge_current = ScaledRegister( 0x05, 0xF0, 4, 64, 64 )
    # reg 06 - we don't want to change this
    # recharge_threshold_offset = Register( 0x06, 0x01, 0, 0, 0 )
    # precharge_threshold = Register( 0x06, 0x01, 0, 0 ,0 )
    # charge_voltage_limit = Register( 0x06, 0xFC, 2, 0.016, 3.84 )
    # reg 07
    fast_charge_timer = Register(0x07, 0x06, 1)
    charge_safety_timer_enable = Register(0x07, 0x08, 3)
    watchdog_timer_setting = Register(0x07, 0x30, 4)
    status_led_disable = Register(0x07, 0x40, 6)
    enable_termination = Register(0x07, 0x80, 7)
    # reg 08
    # we don't use the thermistor
    # we don't use the resistance compensation as we don't control the battery leads.
    # vclamp = Register( 0x08, 0x1C, 2, 32, 0 )
    # compensation_offset = Register(0x08, 0xE0, 5, 20, 0 )
    # reg 09
    # PD being handled by FUSB
    # pulse_control_down = Register( 0x09, 0x01, 0 )
    # pulse_control_up = Register( 0x09, 0x02, 1 )
    batfet_reset = Register(0x09, 0x04, 2)
    batfet_delay_off = Register(0x09, 0x08, 3)
    batfet_disable = Register(0x09, 0x20, 5)
    # we don't do DPM or thermal regulation
    # timer_slowdown = Register( 0x09, 0x40, 6 )
    force_ICO = Register(0x09, 0x80, 7)
    # reg 0A
    # we want this at the default
    # boost_setpoint = ScaledRegister( 0x0A, 0xF0, 4, 4.55, 0.0064 )
    # reg 0B read only
    Vsys_status = Register(0x0B, 0x01, 0)
    USB_input_status = Register(0x0B, 0x02, 1)
    power_good_status = Register(0x0B, 0x04, 2)
    charge_status = Register(0x0B, 0x18, 3)
    Vbus_status = Register(0x0B, 0xE0, 5)
    # reg 0C read only
    # thermistor not used
    battery_fault = Register(0x0C, 0x08, 3)
    charge_fault = Register(0x0C, 0x30, 4)
    boost_fault = Register(0x0C, 0x40, 6)
    watchdog_fault = Register(0x0C, 0x80, 7)
    # reg 0D read only
    absolute_VINDPM_threshold = ScaledRegister(0x0D, 0x7F, 0, 0.2, 2.6)
    force_abolute_threshold = Register(0x0D, 0x80, 7)
    # reg 0E read only
    battery_voltage = ScaledRegister(0x0E, 0x7F, 0, 0.02, 2.304)
    # thermal status not used
    # reg 0F read only
    system_voltage = ScaledRegister(0x0F, 0x7F, 0, 0.02, 2.304)
    # reg 10 read only
    # thermistor not used
    # reg 11 read only
    Vbus_voltage = ScaledRegister(0x11, 0x7F, 0, 0.1, 2.6)
    Vbus_good = Register(0x11, 0x80, 7)
    # reg 12 read only
    charge_current = ScaledRegister(0x12, 0x7F, 0, 0.05, 0)
    # reg 13 read only
    DPM_current_limit = ScaledRegister(0x13, 0x3F, 0, 50, 100)
    IINDPM_status = Register(0x13, 0x40, 6)
    VINDPM_status = Register(0x13, 0x80, 7)
    # reg 14
    # device_revision = Register( 0x14, 0x03, 0 ) always reads 01
    # temperature profile not used
    # part_no = Register( 0x14, 0x38, 3 ) alwyas reads 111
    ICO_status = Register(0x14, 0x40, 3)
    register_reset = Register(0x14, 0x80, 7)

    # bit lists
    charging_status_list = [
        "Not Charging",
        "Pre-Charging",
        "Fast Charging",
        "Terminated",
    ]
    Vbus_status_list = [
        "No Input",
        "USB Host SDP",
        "USB CDP",
        "USB DCP",
        "Adjustable HV DCP",
        "Unkown Adapter",
        "Non Standard Adapter",
        "OTG",
    ]
    USB_input_status_list = ["USB 100", "USB 500"]
    Vsys_regulation_status_list = ["Not in Vsys Regulation", "In Vsys Regulation"]
    power_good_status_list = ["Power not good", "Power good"]
    battery_fault_list = ["Normal", "Battery Over Voltage"]
    charge_fault_list = ["Normal", "Input Fault", "Thermal Shutdown", "Safety Timer"]
    boost_fault_list = ["Normal", "Overloaded, Over Voltage or Battery Low"]
    watchdog_fault_list = ["Normal", "Timer Expired"]
    fault_dict = dict(
        [
            ("Battery", battery_fault_list),
            ("Charge", charge_fault_list),
            ("Boost", boost_fault_list),
            ("Watchdog", watchdog_fault_list),
        ]
    )
    status_dict = dict(
        [
            ("VsysRegulation", Vsys_regulation_status_list),
            ("USB input", USB_input_status_list),
            ("power good", power_good_status_list),
            ("Charge", charging_status_list),
            ("Vbus", Vbus_status_list),
        ]
    )

    # helpers
    def read_bits(self, register):
        """
        Returns a value from selected bits of a register

        Args:
            register(Register): a namedtuple containing
                -register
                -mask
                -position
        :rtype: (int)
        """
        regVal = self.i2c.readfrom_mem(self.ADDRESS, register.register, 1)[0]
        return (regVal & register.mask) >> register.position

    def write_bits(self, register, value):
        """
        Writes a value to selected bits of a register

        Args:
            register(Register): a namedtuple containing
                -register
                -mask
                -position
        """
        regVal = self.i2c.readfrom_mem(self.ADDRESS, register.register, 1)[0]
        regVal = regVal & (~register.mask)
        regVal = regVal | (value << register.position)
        self.i2c.writeto_mem(self.ADDRESS, register.register, bytes([regVal]))

    def read_scaled(self, scaledregister):
        """
        Returns a value from a register entry and applies scaling and offset.

        Args:
            scaledregister(ScaledRegister): a namedtuple containing
                -register
                -mask
                -position
                -scaling
                -offset
        :rtype: (float)
        """
        regVal = self.i2c.readfrom_mem(self.ADDRESS, scaledregister.register, 1)[0]
        return (
            float((regVal & scaledregister.mask) >> scaledregister.position)
            * scaledregister.scaling
        ) + scaledregister.offset

    def write_scaled(self, scaledregister, value):
        """
        write a scaled value to a register entry.

        Args:
            scaledregister(ScaledRegister): a namedtuple containing
                -register
                -mask
                -position
                -scaling
                -offset
            value(float): value to be scaled
        """
        regVal = self.i2c.readfrom_mem(self.ADDRESS, scaledregister.register, 1)[0]
        regVal = regVal & (~scaledregister.mask)
        temp = (
            int((value - scaledregister.offset) / scaledregister.scaling)
            << scaledregister.position
        ) & scaledregister.mask
        regVal = regVal | temp
        self.i2c.writeto_mem(self.ADDRESS, scaledregister.register, bytes([regVal]))

    def enable_conversion(self, enable=True, single=False):
        """
        Start a one shot conversion of the ADCs or enable or disable the conversion at a 1Hz rate

        Args:
            enable (bool): if True enable the converion.
                if False disable the converter.
                not used for if single is True.
            single (bool): if True start a single ADC conversion
        """
        if single:
            self.write_bits(self.conversion_rate, 1)
        else:
            if enable:
                self.write_bits(self.conversion_start, 1)
            else:
                self.write_bits(self.conversion_start, 0)

    def enable_HiZ_input(self, enable):
        """
        Put the converter into High impedance mode on the input to prevent current draw or take it out of HiZ mode

        Args:
            enable (bool): if True enable the high impedance mode
                if False disable the high impedance mode
        """
        if enable:
            self.write_bits(self.enable_HiZ, 1)
        else:
            self.write_bits(self.enable_HiZ, 0)

    def enable_boost(self, enable=True):
        """
        Control the boost output

        Args:
            enable (bool): if True enable boost converter
                if False disable the boost converter
        """
        if enable:
            self.write_bits(self.otg_boost, 1)
        else:
            self.write_bits(self.otg_boost, 0)

    def disconnect_battery(self):
        """
        Disconnect the battery from the IC
        """
        self.write_bits(self.batfet_disable, 1)

    def connect_battery(self):
        """
        Connect the battery to the IC
        """
        self.write_bits(self.batfet_disable, 0)

    def set_input_current_limit(self, limit):
        """
        Set the Input current limit

        Args:
            limit (int): Limit in mA, range 100-3250mA resolution 50mA
        """
        self.write_scaled(self.input_Ilim, limit)

    def get_status(self):
        """
        Returns the decoded status read from the device
        Do not use from an ISR

        :rtype: (dict)
        """
        read = self.i2c.readfrom_mem(self.ADDRESS, 0x0B, 1)[0]
        status = dict(
            [
                ("VsysRegulation", 0),
                ("USB input", 0),
                ("power good", 0),
                ("Charge", 0),
                ("Vbus", 0),
            ]
        )
        status["VsysRegulation"] = (
            read & self.Vsys_status.mask
        ) >> self.Vsys_status.position
        status["USB input"] = (
            read & self.USB_input_status.mask
        ) >> self.USB_input_status.position
        status["power good"] = (
            read & self.power_good_status.mask
        ) >> self.power_good_status.position
        status["Charge"] = (
            read & self.charge_status.mask
        ) >> self.charge_status.position
        status["Vbus"] = (read & self.Vbus_status.mask) >> self.Vbus_status.position
        return status

    def get_fault(self):
        """
        Returns the decoded faults, reads the register twice to ensure previous faults are cleared
        Do not use from an ISR

        :rtype: (dict)
        """
        read = self.i2c.readfrom_mem(self.ADDRESS, 0x0C, 1)[0]
        read = self.i2c.readfrom_mem(self.ADDRESS, 0x0C, 1)[0]
        fault = dict([("Battery", 0), ("Charge", 0), ("Boost", 0), ("Watchdog", 0)])
        fault["Battery"] = (
            read & self.battery_fault.mask
        ) >> self.battery_fault.position
        fault["Charge"] = (read & self.charge_fault.mask) >> self.charge_fault.position
        fault["Boost"] = (read & self.boost_fault.mask) >> self.boost_fault.position
        fault["Watchdog"] = (
            read & self.watchdog_fault.mask
        ) >> self.watchdog_fault.position
        return fault

    def get_Vbat(self):
        """
        Returns the battery Voltage

        :rtype: (float)
        """
        return self.read_scaled(self.battery_voltage)

    def get_Vsys(self):
        """
        Returns the System output Voltage

        :rtype: (float)
        """
        return self.read_scaled(self.system_voltage)

    def get_Vbus(self):
        """
        Returns the Vbus input Voltage

        :rtype: (float)
        """
        return self.read_scaled(self.Vbus_voltage)

    def get_DPM_current_limit(self):
        """
        Returns current limit determined by dynamic power management

        :rtype: (float)
        """
        return self.read_scaled(self.DPM_current_limit)

    def reset(self):
        """
        Reset the device to a known state.
        """
        self.write_bits(self.register_reset, 1)

    def init(self):
        """
        Initialise the bq25895 to the state we want
        """
        # reset ic to known state
        self.reset()
        # use single byte writes to reduce I2C traffic instead of read modify write since we just reset registers to known values
        # Leave input current limit (REG0x00 at 500mA until PD is complete
        # Disable the boost output, leave minimum system voltage at 3.5V and charging enabled
        self.i2c.writeto_mem(self.ADDRESS, 0x03, bytes([0x1A]))
        # start ADC conversions running at a 1s interval and disable detection using D+/D- and ICO
        self.i2c.writeto_mem(self.ADDRESS, 0x02, bytes([0x60]))
        # disable the watchdog to allow charging while apps have control
        self.i2c.writeto_mem(self.ADDRESS, 0x07, bytes([0x8C]))


if __name__ == "__main__":
    from machine import Pin, I2C
    from utime import sleep_ms

    i2c = I2C(0, scl=Pin(46), sda=Pin(45), freq=400000)
    pin_reset_i2c = Pin(9, Pin.OUT)
    pin_reset_i2c.on()
    i2c.writeto(0x77, bytes([(0x1 << 7)]))
    pmic = bq25895(i2c)
    pmic.init()
    # start 1Hz ADC sampling
    pmic.enable_conversion()
    # report status and faults with various methods
    print("Status" + str(pmic.get_status()))
    status = pmic.get_status()
    for key in status:
        print(key + " " + str(pmic.status_dict[key][status[key]]))
    Faults = pmic.get_fault()
    for key in Faults:
        print(key + " " + str(pmic.fault_dict[key][Faults[key]]))
    print("Battery still " + str(pmic.battery_fault_list[Faults["Battery"]]))
    # let the ADC run at least once
    sleep_ms(1000)
    # read the voltages
    print("Battery Voltage = " + str(pmic.get_Vbat()) + "V")
    print("System Voltage = " + str(pmic.get_Vsys()) + "V")
    print("Vbus Voltage = " + str(pmic.get_Vbus()) + "V")
    # read the current
    print("DPM current limit = " + str(pmic.get_DPM_current_limit()) + "mA")
