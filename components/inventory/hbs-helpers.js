
const hbsHelpers = {
    debug: function(val, options) {
        console.log(val);
        return "check you console log";
    },
    eq: function(val1, val2, options) {
        return val1 === val2;
    },
    neq: function(val1, val2, options) {
        return val1 !== val2;
    },
    ternary: function(condition, onTrue, onFalse, options) {
        return condition ? onTrue : onFalse;
    }
};

export { hbsHelpers };
