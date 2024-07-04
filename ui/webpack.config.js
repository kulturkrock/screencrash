// Config file, uses require imports
// eslint-disable-next-line @typescript-eslint/no-var-requires
const path = require("path");

module.exports = {
  target: "web",
  mode: "development",
  devtool: "source-map",

  entry: {
    bundle: path.resolve(__dirname, "./src/tsx/main.tsx"),
  },

  output: {
    filename: "[name].js",
    path: path.resolve(__dirname, "./dist/webpack"),
    publicPath: "/webpack/",
  },

  module: {
    rules: [
      {
        test: /\.tsx?$/,
        loaders: "ts-loader",
        exclude: /node_modules/,
      },
      {
        test: /\.less$/,
        use: [
          {
            loader: "style-loader",
          },
          {
            loader: "css-loader",
            options: {
              modules: {
                localIdentRegExp: "([^/\\\\]*).module.less",
                localIdentName: "[1]__[local]",
              },
            },
          },
          {
            loader: "less-loader",
          },
        ],
      },
      {
        test: /\.pdf$/,
        use: [
          {
            loader: "url-loader",
          },
        ],
      },
    ],
  },

  optimization: {
    runtimeChunk: "single",
    splitChunks: {
      cacheGroups: {
        vendor: {
          test: /node_modules/,
          name: "vendor",
          enforce: true,
          chunks: "all",
        },
      },
    },
  },

  resolve: {
    extensions: [".ts", ".tsx", ".js", ".jsx", ".less"],
  },
};
