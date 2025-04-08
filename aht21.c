#include "aht21.h"

static uint8_t aht21_addr_local = 0x38;

uint8_t AHT21_CalibrateCMD[3] = {0xE1, 0x08, 0x00};
uint8_t AHT21_NormalCMD[3]    = {0xA8, 0x00, 0x00};
uint8_t AHT21_MeasureCMD[3]   = {0xAC, 0x33, 0x00};
uint8_t AHT21_ResetCMD        = 0xBA;


static esp_err_t i2c_master_read_slave(i2c_port_t i2c_num, uint8_t i2c_addr, uint8_t* data_rd, size_t size)
{
    if (size == 0) {
        return ESP_OK;
    }
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    // send register we want
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

static esp_err_t i2c_master_write_slave(i2c_port_t i2c_num, uint8_t i2c_addr, uint8_t* data_wr, size_t size)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    // first, send device address (indicating write) & register to be written
    i2c_master_write_byte(cmd, ( i2c_addr << 1 ) | I2C_MASTER_WRITE, 1);
    // write the data
    i2c_master_write(cmd, data_wr, size, 1);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(i2c_num, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}
void AHT21_SET_ID(uint8_t aht21_addr){
    aht21_addr_local = aht21_addr;
}
esp_err_t AHT21_TRIGGER_MEASUREMENT(i2c_port_t i2c_num){
    return i2c_master_write_slave(i2c_num, aht21_addr_local, AHT21_MeasureCMD, sizeof(AHT21_MeasureCMD));
}
esp_err_t AHT21_CALIBRATION(i2c_port_t i2c_num){
    return i2c_master_write_slave(i2c_num, aht21_addr_local, AHT21_CalibrateCMD, sizeof(AHT21_CalibrateCMD));
}
esp_err_t AHT21_RESET(i2c_port_t i2c_num){
    return i2c_master_write_slave(i2c_num, aht21_addr_local, &AHT21_ResetCMD, sizeof(AHT21_ResetCMD));
}
esp_err_t AHT21_READ_TEMP(i2c_port_t i2c_num, float* temp){
    esp_err_t ret;
    uint8_t data_rd[6] ={0};
    //uint32_t temp = 0;
    ret = i2c_master_read_slave(i2c_num, aht21_addr_local, data_rd, 6);
    if(ret == ESP_OK){
       *temp = ((((float)(((data_rd[3] & 0x0F) << 16) | (data_rd[4] << 8) | data_rd[5]))*200)/1048576)-50;
    }
    return ret;
}
esp_err_t AHT21_READ_RH(i2c_port_t i2c_num, float* rHum){
    esp_err_t ret;
    uint8_t data_rd[6] ={0};
    ret = i2c_master_read_slave(i2c_num, aht21_addr_local, data_rd, 6);
    if(ret == ESP_OK){
       *rHum = (((float)(((data_rd[1]) << 16| (data_rd[2] << 8) | data_rd[3])>>4)*100)/1048576);
    }
    return ret;
}