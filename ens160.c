#include "ens160.h"


static uint8_t ens160_addr_local = 0x53;

static esp_err_t i2c_master_read_slave_reg(i2c_port_t i2c_num, uint8_t i2c_addr, uint8_t i2c_reg, uint8_t* data_rd, size_t size)
{
    if (size == 0) {
        return ESP_OK;
    }
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    // first, send device address (indicating write) & register to be read
    i2c_master_write_byte(cmd, ( i2c_addr << 1 ), 1);
    // send register we want
    i2c_master_write_byte(cmd, i2c_reg, 1);
    // Send repeated start
    i2c_master_start(cmd);
    // now send device address (indicating read) & read data
    i2c_master_write_byte(cmd, ( i2c_addr << 1 ) | I2C_MASTER_READ, 0);
    
    if (size > 1) {
        i2c_master_read(cmd, data_rd, size - 1, 0);
    }
    
    i2c_master_read_byte(cmd, data_rd + size - 1, 1);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(i2c_num, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}

static esp_err_t i2c_master_write_slave_reg(i2c_port_t i2c_num, uint8_t i2c_addr, uint8_t i2c_reg, uint8_t* data_wr, size_t size)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    // first, send device address (indicating write) & register to be written
    i2c_master_write_byte(cmd, ( i2c_addr << 1 ) | I2C_MASTER_WRITE, 1);
    // send register we want
    i2c_master_write_byte(cmd, i2c_reg, 1);
    // write the data
    i2c_master_write(cmd, data_wr, size, 1);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(i2c_num, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}
void ENS160_SET_ID(uint8_t ens160_addr){
    ens160_addr_local = ens160_addr;
}
esp_err_t ENS160_MODE_SET(i2c_port_t i2c_num, uint8_t mode){
     return i2c_master_write_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_OPMODE, &mode, 1);
}
esp_err_t ENS160_READ_MODE(i2c_port_t i2c_num, uint8_t* mode){
    return i2c_master_read_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_OPMODE, mode, 1);
}
esp_err_t ENS160_GET_STATUS(i2c_port_t i2c_num, uint8_t* status){
    return i2c_master_read_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_DATA_STATUS, status, 1);
}
esp_err_t ENS160_GET_eCO2(i2c_port_t i2c_num, uint16_t* eco2){
    uint8_t data[2] = {0};
    esp_err_t ret = i2c_master_read_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_DATA_ECO2, data, 2);
    *eco2 = (data[1]<<8)|data[0];
    return ret;
}
esp_err_t ENS160_SET_TEMP_IN(i2c_port_t i2c_num, float temp){
    uint8_t data[2] = {0};
    int16_t scaled_value = (int16_t)(temp * 64.0f);

    // Clamp the value to the valid range for 10-bit integer + 6-bit fractional part
    if (scaled_value > 32767) scaled_value = 32767; // Ensure it fits in int16_t
    else if (scaled_value < -32768) scaled_value = -32768;

    // Split into two 8-bit bytes
    data[0] = (uint8_t)((scaled_value >> 8) & 0xFF); // High byte
    data[1] = (uint8_t)(scaled_value & 0xFF);        // Low byte
    return i2c_master_write_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_TEMP_IN, data, 2);
}
esp_err_t ENS160_SET_RH_IN(i2c_port_t i2c_num, float rh){
    uint8_t data[2] = {0};
    int16_t scaled_value = (int16_t)(rh * 512.0f);

    // Clamp the value to the valid range for 10-bit integer + 6-bit fractional part
    if (scaled_value > ((127 << 9) | 511)) { // Max value: 127.998046875%
        scaled_value = ((127 << 9) | 511);
    }

    // Split into two 8-bit bytes
    data[0] = (uint8_t)((scaled_value >> 8) & 0xFF); // High byte
    data[1] = (uint8_t)(scaled_value & 0xFF);        // Low byte
    return i2c_master_write_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_RH_IN, data, 2);
}
esp_err_t ENS160_GET_AQI(i2c_port_t i2c_num, uint8_t* aqi){
    esp_err_t ret = i2c_master_read_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_AQI, aqi, 1);
    *aqi = *aqi & 0x07; // mask all but lowest 3 bits;
    return ret;
}
esp_err_t ENS160_GET_TVOC(i2c_port_t i2c_num, uint16_t* tvoc){
    uint8_t data[2] = {0};
    esp_err_t ret = i2c_master_read_slave_reg(i2c_num, ens160_addr_local, ENS160_REG_TVOC, data, 2);
    *tvoc = (data[1]<<8)|data[0];
    return ret;
}