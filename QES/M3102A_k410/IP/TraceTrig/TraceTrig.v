`timescale 1ns / 1ps
//*****************************************************************************
//
// Vendor             : UBC QSTL
// Version            : 1.0
// Application        : Trace Trigger Controller
// Filename           : TraceTrig.v
// Date Last Modified : 2025/10/07
// Date Created       : 2025/10/07
//
// (c) Copyright 2025 - 2025 UBC QSTL. All rights reserved.
//
// Engineer: UBC ECE Jeonghyun Park jeonghyun.park@ubc.ca
// Module Name: TraceTrig
// Project Name: QES Pathwave
// Target Devices: Keysight Virtex series (M3102A Digitizer)
// Tool Versions: 2017.3
// 
// Dependencies: None
// 
// Revision:
//      Revision 0.01 - File Created
//
// Additional Comments:
// 
//*****************************************************************************

module TraceTrig
#(
    parameter integer LEN_WIDTH     = 16,
    parameter integer ACCUM_WIDTH   = 16
)(
    input wire                      clk,
    input wire                      rst_n,
    input wire                      init,
    input wire [ACCUM_WIDTH - 1:0]  accum_num_set,
    input wire [ACCUM_WIDTH - 1:0]  accum_num,
    input wire [LEN_WIDTH - 1:0]    length,
    input wire [4:0]                trigger_in,
    input wire                      saxis_tvalid,
    input wire [79:0]               saxis_tdata,

    output reg [4:0]                maxis_tuser,
    output reg                      maxis_tvalid,
    output reg [79:0]               maxis_tdata,
    output reg                      start,
    output reg                      abort,
    output reg [4:0]                daq_trigger
);
localparam  IDLE        = 2'b00,
            INIT        = 2'b01,
            LAST        = 2'b10;


reg [LEN_WIDTH - 1:0]   length_cnt;
reg                     length_valid;
reg [1:0]               state;

always @(posedge clk) begin
    if (!rst_n) begin
        maxis_tuser     <= 5'd0;
        maxis_tdata     <= 80'd0;
        maxis_tvalid    <= 1'b0;

        start           <= 1'b0;
        abort           <= 1'b0;
        daq_trigger     <= 5'd0;
        length_cnt      <= {LEN_WIDTH{1'b0}};
        length_valid    <= 1'b0;
    end
    else begin
        start           <= 1'b0;
        maxis_tdata     <= saxis_tdata;
        maxis_tvalid    <= saxis_tvalid;
        maxis_tuser     <= trigger_in;
        daq_trigger     <= 5'd0;

        case (state)
            IDLE: begin
                abort       <= 1'b0;
                if (init) begin
                    state       <= INIT;
                    abort       <= 1'b1;
                    start       <= 1'b0;
                    length_cnt  <= {LEN_WIDTH{1'b0}};
                end
                else begin
                    abort       <= 1'b0;
                end
                if ((|trigger_in) && accum_num == accum_num_set) begin
                    state       <= LAST;
                    daq_trigger <= trigger_in;
                    length_cnt  <= length;
                end
            end
            INIT: begin
                abort           <= 1'b0;
                start           <= 1'b1;
                if (init == 1'b0) begin
                    state       <= IDLE;
                end
            end
            LAST: begin
                length_cnt      <= length_cnt - 5;
                if (init) begin
                    state       <= INIT;
                    abort       <= 1'b1;
                    start       <= 1'b0;
                end
                if (length_cnt <= 5) begin
                    state       <= IDLE;
                    start       <= 1'b1;
                end
            end
            default: state      <= IDLE;
        endcase
    end
end

endmodule