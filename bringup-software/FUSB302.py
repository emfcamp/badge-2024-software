"""
FUSB302 Programmable USB Type-C Controller w/PD driver in MicroPython. 

The driver supports basic read write access with some helpers

This is a work in progress. 

"""

from micropython import const
from collections import namedtuple

class fusb302:
    """
    FUSB302 driver class to allow access to registers
    
    Args:
        i2c_instance (I2C)
        
    Attributes:
        lots of register entries...
            
    """        
    def __init__( self, i2c_instance ):
        self.i2c = i2c_instance
    
    # address
    ADDRESS = const(0x22)

    Register = namedtuple('Register', ['register', 'mask', 'position'])
    ScaledRegister = namedtuple('ScaledRegister', ['register', 'mask', 'position', 'scaling', 'offset'])
    
    #reg 01 Device ID
    revision_id = Register( 0x01, 0x0F, 0 )
    version_id = Register( 0x01, 0xF0, 4 )
    # reg 02 Switches0
    pulldown_cc1 = Register( 0x02, 0x01, 0 )
    pulldown_cc2 = Register( 0x02, 0x02, 1 )
    measure_cc1 = Register( 0x02, 0x04, 2 )
    measure_cc2 = Register( 0x02, 0x08, 3 )
    Vconn_on_cc1 = Register( 0x02, 0x10, 4 )
    Vconn_on_cc2 = Register( 0x02, 0x20, 5 )
    host_current_on_cc1 = Register( 0x02, 0x40, 6 )
    host_current_on_cc2 = Register( 0x02, 0x80, 7 )
    # reg 03 Switches1
    enable_bmc_cc1 = Register( 0x03, 0x01, 0 )
    enable_bmc_cc2 = Register( 0x03, 0x02, 1 )
    auto_crc = Register( 0x03, 0x04, 2 )
    datarole = Register( 0x03, 0x10, 4 )
    spec_revision = Register( 0x03, 0x60, 5 )
    power_role = Register( 0x03, 0x80, 7 )
    # reg 04 Measure
    measurement_Vcc = ScaledRegister( 0x04, 0x3F, 0, 42, 42  )
    measurement_Vbus = ScaledRegister( 0x04, 0x3F, 0, 42, 420  )
    measure_Vbus = Register( 0x04, 0x40, 6 )
    # reg 05 slice
    bmc_slicer = Register( 0x05, 0x1F, 0 )
    slicer_hysteresis = Register( 0x05, 0xC0, 6 ) 
    # reg 06 control 0
    start_transmitter = Register( 0x06, 0x01, 0 )
    autostart_tx_on_crc = Register( 0x06, 0x02, 1 )
    host_current = Register( 0x06, 0x0C, 2 )
    interrupt_mask = Register( 0x06, 0x20, 4 )
    tx_flush = Register( 0x06, 0x40, 6 ) 
    # reg 07 control 1
    enable_sop = Register( 0x07, 0x01, 0 )
    enable_sop_double = Register( 0x07, 0x02, 1 )
    rx_flush = Register( 0x07, 0x04, 2 )
    bist_pattern = Register( 0x07, 0x10, 4 )
    enable_sop_debug = Register( 0x07, 0x20, 5 )
    enable_sop_debug_double = Register( 0x07, 0x40, 6 )
    # reg 08 control 2
    enable_toggle = Register( 0x08, 0x01, 0 )
    toggle_mode = Register( 0x08, 0x06, 1 )
    enable_wake = Register( 0x08, 0x08, 3 )
    enable_toggle_read_only = Register( 0x08, 0x20, 5 )
    toggle_powersave_mode = Register( 0x08, 0xC0, 6 )     
    # reg 09 control 3
    auto_retry = Register( 0x09, 0x01, 0 )
    retries_no = Register( 0x09, 0x06, 2 )
    auto_softreset = Register( 0x09, 0x08, 3 )
    auto_hardreset = Register( 0x09, 0x01, 4 )
    send_hardreset = Register( 0x09, 0x40, 6 )
    # reg 0A 
    mask_bc_level = Register( 0x0A, 0x01, 0 )
    mask_collission = Register( 0x0A, 0x02, 1 )
    mask_wake = Register( 0x0A, 0x02, 2 )
    mask_alert = Register( 0x0A, 0x04, 3 )
    mask_crc = Register( 0x0A, 0x10, 4 )
    mask_comparator_change = Register( 0x0A, 0x20, 5 )
    mask_activity = Register( 0x0A, 0x40, 6 )
    mask_vbus_ok = Register( 0x0A, 0x80, 7 ) 
    # reg 0B power control
    enable_oscillator = Register( 0x0B, 0x01, 0 )
    enable_measure = Register( 0x0B, 0x02, 1 )
    enable_rx_and_ref = Register( 0x0B, 0x04, 2 )
    enable_bandgap_and_wake = Register( 0x0B, 0x08, 3 )
    # reg 0C reset
    register_reset = Register( 0x0C, 0x01, 0 )
    pd_reset = Register( 0x0C, 0x02, 1 )
    # reg 0D ocp
    ocp_cuurent = ScaledRegister( 0x0D, 0x07, 0, 10, 10 )
    ocp_cuurent10 = ScaledRegister( 0x0D, 0x07, 0, 100, 100 )
    ocp_range = Register( 0x0D, 0x80, 3 )
    # reg 0E mask a
    mask_hardreset_int = Register( 0x0E, 0x01, 0 )    
    mask_softreset_int = Register( 0x0E, 0x02, 1 )    
    mask_tx_snet_int = Register( 0x0E, 0x04, 2 )    
    mask_hard_sent_int = Register( 0x0E, 0x08, 3 )    
    mask_retry_fail_int = Register( 0x0E, 0x01, 4 )    
    mask_soft_fail_int = Register( 0x0E, 0x02, 5 )    
    mask_toggle_done_int = Register( 0x0E, 0x04, 6 )    
    mask_ocp_temp_int = Register( 0x0E, 0x08, 7 )    
    # reg 0F mask b
    mask_good_crc_sent_int = Register( 0x0F, 0x01, 0 ) 
    # reg 10 Control4
    toggle_unattahce_exit = Register( 0x10, 0x01, 0 )
    # reg 3C status a read only
    hard_reset_order = Register( 0x3C, 0x01, 0 )
    soft_reset_order = Register( 0x3C, 0x02, 1 )
    power_state = Register( 0x3C, 0x0C, 2 )
    retry_fail = Register( 0x3C, 0x10, 4 )
    soft_fail = Register( 0x3C, 0x20, 5 )
    # reg 3D status 1a
    rx_sop = Register(  0x3D, 0x01, 0 )
    rx_sop_debug = Register(  0x3D, 0x02, 1 )
    rx_sop_double_debug = Register(  0x3D, 0x04, 2 )
    toggle_status = Register(  0x3D, 0x38, 3 )
    # reg 3E interrupt a
    hardreset_int = Register( 0x3E, 0x01, 0 )    
    softreset_int = Register( 0x3E, 0x02, 1 )    
    tx_sent_int = Register( 0x3E, 0x04, 2 )    
    hard_sent_int = Register( 0x3E, 0x08, 3 )    
    retry_fail_int = Register( 0x3E, 0x01, 4 )    
    soft_fail_int = Register( 0x3E, 0x02, 5 )    
    toggle_done_int = Register( 0x3E, 0x04, 6 )    
    ocp_temp_int = Register( 0x3E, 0x08, 7 )    
    # reg 3F interrupt b
    good_crc_sent_int = Register( 0x3F, 0x01, 0 )     
    # reg 40 status0
    bc_level = Register( 0x40, 0x03, 0 )
    wake = Register( 0x40, 0x04, 2 )
    alert = Register( 0x40, 0x80, 3 )
    crc_check = Register( 0x40, 0x10, 4 )
    comparator = Register( 0x40, 0x20, 5 )
    activity = Register( 0x40, 0x40, 6 )
    vbus_ok = Register( 0x40, 0x80, 7 )
    # reg 41 status 1
    ocp = Register( 0x41, 0x01, 0 )
    over_temperature = Register( 0x41, 0x02, 1 )
    tx_fifo_full = Register( 0x41, 0x04, 2 )
    tx_fifo_empty = Register( 0x41, 0x08, 3 )
    rx_fifo_full = Register( 0x41, 0x10, 4 )
    rx_fifo_empty = Register( 0x41, 0x20, 5 )
    rx_sop_prime = Register( 0x41, 0x40, 6 )
    rx_sop_prime_double = Register( 0x41, 0x80, 7 )
    # reg 42 interrupt
    bc_level_int = Register( 0x42, 0x01, 0 )
    colision_int = Register( 0x42, 0x02, 1 )
    wake_int = Register( 0x42, 0x04, 2 )
    alert_int = Register( 0x42, 0x08, 3 )
    crc_check_int = Register( 0x42, 0x10, 4 )
    compare_change_int = Register( 0x42, 0x20, 5 )
    activity_int = Register( 0x42, 0x40, 6 )
    vbus_ok_int = Register( 0x42, 0x80, 7 )
    # reg 43 fifo access
    rxtx_fifo = Register( 0x43, 0xFF, 0 )
    
    # FIFO tokens
    TXON       = const( 0xA1 )
    TX_SOP1    = const( 0x12 )
    TX_SOP2    = const( 0x13 )
    TX_SOP3    = const( 0x1B )
    TX_RESET1  = const( 0x15 )
    TX_RESET2  = const( 0x16 )
    TX_PACKSYM = const( 0x80 )
    TX_JAM_CRC = const( 0xFF )
    TX_EOP     = const( 0x14 )
    TX_OFF     = const( 0xFE )
    RX_SOP     = const( 0xE0 )
    RX_SOP1    = const( 0xC0 )
    RX_SOP2    = const( 0xA0 )
    RX_SOP1DB  = const( 0x80 )
    RX_SOP2DB  = const( 0x60 )
        
    #helpers
    def read_bits( self, register ):
        """
        Returns a value from selected bits of a register
        
        Args:
            register(Register): a namedtuple containing
                -register
                -mask
                -position
        :rtype: (int)
        """
        regVal = self.i2c.readfrom_mem( self.ADDRESS, register.register, 1 )
        return ( ( regVal & register.mask) >> register.position ) 
    
    def write_bits( self, register, value ):
        """
        Writes a value to selected bits of a register
        
        Args:
            register(Register): a namedtuple containing
                -register
                -mask
                -position
        """
        regVal = self.i2c.readfrom_mem( self.ADDRESS, register.register, 1 )
        regVal = regVal & (~register.mask)
        regVal = regVal | ( value << register.position )
        self.i2c.writeto_mem( self.ADDRESS, register, regVal )
    
    def read_scaled( self, scaledregister ):
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
        regVal = self.i2c.readfrom_mem( self.ADDRESS, scaledregister.register, 1 )
        return ( float( ( regVal & scaledregister.mask ) >> scaledregister.position ) * scaledregister.scaling ) + scaledregister.offset
    
    def write_scaled( self, scaledregister, value ):
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
        regVal = self.i2c.readfrom_mem( self.ADDRESS, scaledregister.register, 1 )
        regVal = regVal & (~scaledregister.mask)
        temp = ( int(( value - scaledregister.offset ) / scaledregister.scaling ) << scaledregister.position ) & scaledregister.mask
        regVal = regVal | int(temp)
        self.i2c.writeto_mem( self.ADDRESS, scaledregister, regVal )
    
    def set_bit( self, register, input_byte, value ):
        """
        Set bit or bits of the input byte and return.
        
        Args:
            scaledregister(Register): a namedtuple containing
                -register
                -mask
                -position
            input_byte(int): the byte to combine with the scaled data
            value(float): value to be scaled
            
        :rtype: (int)
        """
        return ( ( input_byte & (~register.mask) ) | ( value << register.position ) )
         
    def set_scaled( self, scaledregister, input_byte, value ):
        """
        Scale a value to the register entries scaling and set the bits in the byte
        
        Args:
            scaledregister(ScaledRegister): a namedtuple containing
                -register
                -mask
                -position
                -scaling
                -offset
            input_byte(int): the byte to combine with the scaled data
            value(float): value to be scaled
            
        :rtype: (int)
        """
        temp = ( int(( value - scaledregister.offset ) / scaledregister.scaling ) << scaledregister.position ) & scaledregister.mask
        return ( ( input_byte & (~scaledregister.mask) ) | temp )
    
    def reset( self ):
        """
        Reset the registers to a known state
        """
        self.write_bits( self.register_reset, 1 )
        
    def reset_PD( self ):
        """
        Reset the PD logic
        """
        self.write_bits( self.reset_PD, 1 )
        
    def power_up( self ):
        """
        Turn on 
            [0] Bandgap and wake circuit.
            [1]: Receiver powered and current references for Measure block
            [2]: Measure block powered.
            [3]: Enable internal oscillator.(not used?)
        """
        self.i2c.writeto_mem( self.ADDRESS, self.enable_oscillator.register, 0x07 )

    def get_Status0( self ):
        """
        Returns the decoded status0 read from the device
        Do not use from an ISR
        
        :rtype: (dict)
        """
        read = self.i2c.readfrom_mem( self.ADDRESS, self.vbus_ok.register, 1 )
        status = dict( [ 
                ( 'VBUSOK', 0 ),
                ( 'ACTIVITY', 0 ), 
                ( 'COMP', 0 ), 
                ( 'CRC_CHK', 0 ), 
                ( 'ALERT', 0 ), 
                ( 'WAKE', 0 ), 
                ( 'BC_LVL', 0 ) 
                ] )
        status['VBUSOK'] = ( read & self.vbus_ok.mask ) >> self.vbus_ok.position
        status['ACTIVITY'] = ( read & self.activity.mask ) >> self.activity.position
        status['COMP'] = ( read & self.comparator.mask ) >> self.comparator.position
        status['CRC_CHK'] = ( read & self.crc_check.mask ) >> self.crc_check.position
        status['ALERT'] = ( read & self.alert.mask ) >> self.alert.position
        status['WAKE'] = ( read & self.wake.mask ) >> self.wake.position
        status['BC_LVL'] = ( read & self.bc_level.mask ) >> self.bc_level.position
        return status
    
    def get_status1( self ):
        """
        Returns the decoded status1 read from the device
        Do not use from an ISR
               
        :rtype: (dict)
        """
        read = self.i2c.readfrom_mem( self.ADDRESS, self.vbus_ok.register, 1 )
        status = dict( [ 
                ( 'OCP', 0 ), 
                ( 'OVRTEMP', 0 ), 
                ( 'TX_FULL', 0 ), 
                ( 'TX_EMPTY', 0 ), 
                ( 'RX_FULL', 0 ), 
                ( 'RX_EMPTY', 0 ), 
                ( 'RXSOP1', 0 ), 
                ( 'RXSOP2', 0 ) ] )
        status['OCP'] = ( read & self.ocp.mask ) >> self.ocp.position
        status['OVRTEMP'] = ( read & self.over_temperature.mask ) >> self.over_temperature.position
        status['TX_FULL'] = ( read & self.tx_fifo_full.mask ) >> self.tx_fifo_full.position
        status['TX_EMPTY'] = ( read & self.tx_fifo_empty.mask ) >> self.tx_fifo_empty.position
        status['RX_FULL'] = ( read & self.rx_fifo_full.mask ) >> self.rx_fifo_full.position
        status['RX_EMPTY'] = ( read & self.rx_fifo_empty.mask ) >> self.rx_fifo_empty.position
        status['RXSOP1'] = ( read & self.rx_sop_prime.mask ) >> self.rx_sop_prime.position
        status['RXSOP2'] = ( read & self.rx_sop_prime_double.mask ) >> self.rx_sop_prime_double.position
        return status
        
    def get_status0a( self ):
        """
        Returns the decoded status0a read from the device
        Do not use from an ISR
               
        :rtype: (dict)
        """
        read = self.i2c.readfrom_mem( self.ADDRESS, self.vbus_ok.register, 1 )
        status = dict( [ ( 'HARDRST', 0 ), ( 'SOFTRST', 0 ), ( 'POWER', 0 ), ( 'RETRYFAIL', 0 ), ( 'SOFTFAIL', 0 ) ] )
        status['HARDRST'] = ( read & self.hard_reset_order.mask ) >> self.hard_reset_order.position
        status['SOFTRST'] = ( read & self.soft_reset_order.mask ) >> self.soft_reset_order.position
        status['POWER'] = ( read & self.power_state.mask ) >> self.power_state.position
        status['RETRYFAIL'] = ( read & self.retry_fail.mask ) >> self.retry_fail.position
        status['SOFTFAIL'] = ( read & self.soft_fail.mask ) >> self.soft_fail.position
        return status
    
    def get_status1a( self ):
        """
        Returns the decoded status1a read from the device
        Do not use from an ISR
        
        :rtype: (dict)
        """
        read = self.i2c.readfrom_mem( self.ADDRESS, self.vbus_ok.register, 1 )
        status = dict( [ 
            ( 'RXSOP', 0 ),
            ( 'RXSOP1DB', 0 ), 
            ( 'RXSOP2DB', 0 ), 
            #( 'TOGSS', 0 )
              ] )
        status['RXSOP'] = ( read & self.rx_sop.mask ) >> self.ocp.position
        status['RXSOP1DB'] = ( read & self.rx_sop_debug.mask ) >> self.rx_sop_debug.position
        status['RXSOP2DB'] = ( read & self.rx_sop_double_debug.mask ) >> self.rx_sop_double_debug.position
        #status['TOGSS'] = ( read & self.toggle_status.mask ) >> self.toggle_status.position
        return status
        
    def get_interrupts( self ):
        """
        amalgamate the interrupts and return a dict containing a flag for each
        Do not use from an ISR...
        
        :rtype: (dict)
        """
        Interrupta = self.i2c.readfrom_mem( self.ADDRESS, self.hardreset_int.register, 1 )
        Interruptb = self.i2c.readfrom_mem( self.ADDRESS, self.good_crc_sent_int.register, 1 )
        Interrupt = self.i2c.readfrom_mem( self.ADDRESS, self.bc_level_int.register, 1 )
        current_interrupts = dict( [ 
                ( 'I_HARDRST', 0 ), 
                ( 'I_SOFTRST', 0 ), 
                ( 'I_TXSENT', 0 ), 
                ( 'I_HARDSENT', 0 ), 
                ( 'I_RETRYFAIL', 0 ), 
                ( 'I_SOFTFAIL', 0 ), 
                #( 'I_TOGDONE', 0 ), 
                ( 'I_OCP_TEMP', 0 ), 
                ( 'I_GCRCSENT', 0 ), 
                ( 'I_BC_LVL', 0 ), 
                ( 'I_COLLISION', 0 ), 
                ( 'I_WAKE', 0 ), 
                ( 'I_ALERT', 0 ), 
                ( 'I_CRC_CHK', 0 ), 
                ( 'I_COMP_CHNG', 0 ), 
                ( 'I_ACTIVITY', 0 ), 
                ( 'I_VBUSOK', 0 ) 
                ] )
        current_interrupts['I_HARDRST'] = ( Interrupta & self.hardreset_int.mask ) >> self.hardreset_int.position
        current_interrupts['I_SOFTRST'] = ( Interrupta & self.softreset_int.mask ) >> self.softreset_int.position
        current_interrupts['I_TXSENT'] = ( Interrupta & self.tx_sent_int.mask ) >> self.tx_sent_int.position
        current_interrupts['I_HARDSENT'] = ( Interrupta & self.hard_sent_int.mask ) >> self.hard_sent_int.position
        current_interrupts['I_RETRYFAIL'] = ( Interrupta & self.retry_fail_int.mask ) >> self.retry_fail_int.position
        current_interrupts['I_SOFTFAIL'] = ( Interrupta & self.soft_fail_int.mask ) >> self.soft_fail_int.position
        #current_interrupts['I_TOGDONE'] = ( Interrupta & self.toggle_done_int.mask ) >> self.toggle_done_int.position
        current_interrupts['I_OCP_TEMP'] = ( Interrupta & self.ocp_temp_int.mask ) >> self.ocp_temp_int.position
        current_interrupts['I_GCRCSENT'] = ( Interruptb & self.good_crc_sent_int.mask ) >> self.good_crc_sent_int.position
        current_interrupts['I_BC_LVL'] = ( Interrupt & self.bc_level_int.mask ) >> self.bc_level_int.position
        current_interrupts['I_COLLISION'] = ( Interrupt & self.colision_int.mask ) >> self.colision_int.position
        current_interrupts['I_WAKE'] = ( Interrupt & self.wake_int.mask ) >> self.wake_int.position
        current_interrupts['I_ALERT'] = ( Interrupt & self.alert_int.mask ) >> self.alert_int.position
        current_interrupts['I_CRC_CHK'] = ( Interrupt & self.crc_check_int.mask ) >> self.crc_check_int.position
        current_interrupts['I_COMP_CHNG'] = ( Interrupt & self.compare_change_int.mask ) >> self.compare_change_int.position
        current_interrupts['I_ACTIVITY'] = ( Interrupt & self.activity_int.mask ) >> self.activity_int.position
        current_interrupts['I_VBUSOK'] = ( Interrupt & self.vbus_ok_int.mask ) >> self.vbus_ok_int.position
        return current_interrupts

    def set_overcurrent_protection( self ):
        """
        Set the over current protection level
        """
        
  
    def determine_input_current_limit( self ):
        """ 
        Determine the input current limit
        To be called on attach ( VbusOK rising edge )
        """
        status = self.get_Status0()
        if status[ 'BC_LVL' ] == 0:
            #Ra connected to this CC, change to other CC connection 
            if self.cc_select == 1:
                self.write_bits( self.measure_cc1, 0 )
                self.write_bits( self.measure_cc2, 1 )
                self.cc_select = 2
            else:
                self.write_bits( self.measure_cc2, 0 )
                self.write_bits( self.measure_cc1, 1 )
                self.cc_select = 1
            #re-read status
            status = self.get_Status0()
        #determine current level.
        if status[ 'BC_LVL' ] > 0:
            if status[ 'BC_LVL' ] == 2:
                self.input_current_limit = 1500
            elif status[ 'BC_LVL' ] == 3 and status[ 'COMP' ] == 0:
                self.input_current_limit = 3000
            else:
                #what should this be
                self.input_current_limit = 500
            
                
    
    def reset_input_current_limit( self ):
        """ 
        Reset the input current limit on detach
        To be called on detach (VbusOK falling edge)
        """
        self.input_current_limit = 500
        
    def get_input_current_limit( self ):
        """
        Get the input current limit
        
        :rtype: (int) current in mA
        """
        return self.input_current_limit
        
    def setup_device( self ):
        """
        Initialise the fusb302 to a device
        
        This should be called before any BMC registers are changed.
        """
        # put device into a known state, including toggle off.
        self.reset() 
        # disable all interrupts, we'll configure these as we need them.
        
        self.power_up()
        #set comp threshold to 2.226V
        self.write_scaled( self.measurement_Vcc, 2226 )
        #switch the measurment to cc1 keeping pull downs enabled.
        #self.write_bits( self.measure_cc1, 1 )
        self.i2c.writeto_mem( self.ADDRESS, self.measure_cc1.register, 0x07 )
        # setup over current protection
        
        # setup interrupt masks todo: do we need wake?
        self.i2c.writeto_mem( self.ADDRESS, self.mask_vbus_ok.register, 0xA5 )
        self.i2c.writeto_mem( self.ADDRESS, self.mask_ocp_temp_int.register, 0x80 )
        # register? an isr for the VbusOk for attach detection 
        
        self.input_current_limit = 500
        self.cc_select = 1
        #setup auto retries for PD
        self.write_bits( self.auto_retry, 1 )
        #flush buffers, enable interrupts
        self.write_bits( self.tx_flush, 1 )
        self.write_bits( self.rx_flush, 1 )
        
        #set auto good crc response last as we need to respond within a timeout.
        self.write_bits( self.auto_crc, 1 )
        
    def setup_host( self ):
        """
        Initialise the fusb302 to a device
        """
        self.reset() 
        self.power_up()
        # set power and data roles
        self.i2c.writeto_mem( self.ADDRESS, self.datarole.register, 0xB0 )
        #todo
        
           
        
if __name__ == '__main__':
    from machine import  Pin, I2C
    from utime import sleep_ms
    i2c = I2C(0, scl=Pin(46), sda=Pin(45), freq=400000)
    host = fusb302(i2c)
    switches0 = host.set_bit( host.pulldown_cc1, 0, 1 )
    switches0 = host.set_bit( host.pulldown_cc2, switches0, 1 )
    switches0 = host.set_bit( host.measure_cc1, switches0, 1 )
    switches0 = host.set_bit( host.measure_cc2, switches0, 1 )
    print( switches0 )
    
    measure = host.set_scaled( host.measurement_Vcc, 0, 2646 )
    measure = host.set_bit( host.measure_Vbus, measure, 0 )
    print( measure )    