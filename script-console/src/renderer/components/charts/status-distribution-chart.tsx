import ReactECharts from "echarts-for-react";

export function StatusDistributionChart(props: { items: Array<{ name: string; value: number }> }) {
  return (
    <ReactECharts
      style={{ height: 280 }}
      option={{
        backgroundColor: "transparent",
        tooltip: {
          trigger: "item",
        },
        legend: {
          bottom: 0,
          textStyle: {
            color: "#b3c2d9",
          },
        },
        series: [
          {
            type: "pie",
            radius: ["52%", "76%"],
            avoidLabelOverlap: true,
            label: {
              color: "#dbeafe",
              formatter: "{b}\n{c}",
            },
            itemStyle: {
              borderColor: "#09111c",
              borderWidth: 4,
            },
            data: props.items,
          },
        ],
      }}
    />
  );
}
